"""
Reinforcement Learning Agent for Trade Execution Optimization.

Provides DQN and PPO agents, a gym-like trading environment,
risk-adjusted reward calculation, and walk-forward training/evaluation.
"""

import json
import logging
import math
import os
import pickle
import random
import time
from collections import deque, namedtuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("ml.models.rl_agent")

# ── Constants ───────────────────────────────────────────────────────────

SAVED_MODELS_DIR = Path(__file__).resolve().parent.parent / "saved_models" / "rl"
SAVED_MODELS_DIR.mkdir(parents=True, exist_ok=True)

Experience = namedtuple("Experience", ["state", "action", "reward", "next_state", "done"])

ACTION_HOLD = 0
ACTION_BUY = 1
ACTION_SELL = 2
NUM_ACTIONS = 3

# ── Reward Calculator ───────────────────────────────────────────────────


class RewardCalculator:
    """
    Computes risk-adjusted rewards for RL trading agents.

    Combines Sharpe-ratio-based returns, drawdown penalty,
    transaction cost penalty, and holding-time shaping.
    """

    def __init__(
        self,
        risk_free_rate: float = 0.02,
        sharpe_window: int = 20,
        drawdown_penalty_scale: float = 2.0,
        transaction_cost: float = 0.001,
        holding_bonus: float = 0.001,
        max_holding_steps: int = 50,
    ):
        self.risk_free_rate = risk_free_rate
        self.sharpe_window = sharpe_window
        self.drawdown_penalty_scale = drawdown_penalty_scale
        self.transaction_cost = transaction_cost
        self.holding_bonus = holding_bonus
        self.max_holding_steps = max_holding_steps
        self._returns_buffer: List[float] = []
        self._peak_value: float = 0.0
        self._current_value: float = 0.0
        self._holding_steps: int = 0
        self._last_action: int = ACTION_HOLD

    def reset(self) -> None:
        self._returns_buffer.clear()
        self._peak_value = 0.0
        self._current_value = 0.0
        self._holding_steps = 0
        self._last_action = ACTION_HOLD

    def _sharpe_ratio(self) -> float:
        if len(self._returns_buffer) < 2:
            return 0.0
        arr = np.array(self._returns_buffer[-self.sharpe_window:])
        mean_ret = np.mean(arr)
        std_ret = np.std(arr)
        if std_ret < 1e-10:
            return 0.0
        return (mean_ret - self.risk_free_rate / 252) / std_ret * np.sqrt(252)

    def _max_drawdown(self) -> float:
        if self._peak_value <= 0:
            return 0.0
        return (self._peak_value - self._current_value) / self._peak_value

    def calculate(
        self,
        pnl: float,
        action: int,
        portfolio_value: float,
        position: float,
    ) -> float:
        """
        Compute reward for the current step.

        Args:
            pnl: realised + unrealised P&L for this step.
            action: ACTION_HOLD, ACTION_BUY, or ACTION_SELL.
            portfolio_value: total portfolio value after this step.
            position: current position size (>0 long, <0 short, 0 flat).

        Returns:
            Scalar reward.
        """
        self._current_value = portfolio_value
        self._peak_value = max(self._peak_value, portfolio_value)

        # Return for this step
        if self._peak_value > 0:
            step_return = pnl / self._peak_value
        else:
            step_return = 0.0
        self._returns_buffer.append(step_return)

        # Sharpe component
        sharpe_r = self._sharpe_ratio()
        reward = sharpe_r * 0.1  # scale down

        # Drawdown penalty
        dd = self._max_drawdown()
        if dd > 0.05:
            reward -= dd * self.drawdown_penalty_scale

        # Transaction cost
        if action != ACTION_HOLD:
            reward -= self.transaction_cost
            self._holding_steps = 0
        else:
            self._holding_steps += 1

        # Holding-time shaping
        if position != 0 and self._holding_steps < self.max_holding_steps:
            reward += self.holding_bonus * min(self._holding_steps / self.max_holding_steps, 1.0)
        elif self._holding_steps > self.max_holding_steps:
            reward -= self.holding_bonus * 0.5

        self._last_action = action
        return float(np.clip(reward, -10.0, 10.0))

    def get_metrics(self) -> Dict[str, float]:
        return {
            "sharpe_ratio": self._sharpe_ratio(),
            "max_drawdown": self._max_drawdown(),
            "peak_value": self._peak_value,
            "current_value": self._current_value,
            "holding_steps": self._holding_steps,
            "returns_count": len(self._returns_buffer),
        }


# ── Trading Environment ─────────────────────────────────────────────────


class TradingEnvironment:
    """
    Gym-like trading environment for RL agents.

    State space: OHLCV + indicators + position + P&L.
    Action space: discrete (HOLD / BUY / SELL).
    """

    def __init__(
        self,
        data: np.ndarray,
        feature_columns: Optional[List[int]] = None,
        initial_balance: float = 100_000.0,
        position_size: float = 0.1,
        max_position: float = 1.0,
        episode_length: int = 500,
        reward_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Args:
            data: 2-D array of shape (timesteps, features). Must include
                  columns for open, high, low, close, volume at minimum.
            feature_columns: indices of columns to use as state features.
                             If None, use all columns.
            initial_balance: starting cash.
            position_size: fraction of balance per trade.
            max_position: max position fraction.
            episode_length: steps per episode.
            reward_config: kwargs forwarded to RewardCalculator.
        """
        if data.ndim != 2 or data.shape[0] < 2:
            raise ValueError("data must be a 2-D array with at least 2 rows")

        self.raw_data = data.astype(np.float32)
        self.feature_columns = feature_columns or list(range(data.shape[1]))
        self.initial_balance = initial_balance
        self.position_size = position_size
        self.max_position = max_position
        self.episode_length = episode_length

        self.n_features = len(self.feature_columns)
        # State = features + position (1) + unrealised_pnl_pct (1) + balance_pct (1)
        self.state_dim = self.n_features + 3

        self.reward_calc = RewardCalculator(**(reward_config or {}))

        self._reset_state()

    def _reset_state(self) -> None:
        self._step_idx = 0
        self._balance = self.initial_balance
        self._position = 0.0  # units held (can be negative for short)
        self._entry_price = 0.0
        self._total_pnl = 0.0
        self._trades: List[Dict[str, Any]] = []
        self.reward_calc.reset()

    def reset(self) -> np.ndarray:
        """Reset environment and return initial state."""
        max_start = max(0, self.raw_data.shape[0] - self.episode_length - 10)
        self._step_idx = random.randint(0, max_start) if max_start > 0 else 0
        self._balance = self.initial_balance
        self._position = 0.0
        self._entry_price = 0.0
        self._total_pnl = 0.0
        self._trades = []
        self.reward_calc.reset()
        return self._get_state()

    def _get_state(self) -> np.ndarray:
        row = self.raw_data[self._step_idx, self.feature_columns]
        pos_norm = self._position / self.max_position if self.max_position else 0.0
        current_price = self.raw_data[self._step_idx, 3]  # close assumed col 3
        if self._position != 0 and self._entry_price > 0:
            unrealised = (current_price - self._entry_price) / self._entry_price * np.sign(self._position)
        else:
            unrealised = 0.0
        balance_pct = self._balance / self.initial_balance if self.initial_balance else 0.0
        extras = np.array([pos_norm, unrealised, balance_pct], dtype=np.float32)
        return np.concatenate([row, extras])

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict[str, Any]]:
        """
        Execute one step.

        Returns:
            (next_state, reward, done, info)
        """
        action = int(np.clip(action, 0, NUM_ACTIONS - 1))
        current_price = self.raw_data[self._step_idx, 3]  # close

        trade_info: Optional[Dict[str, Any]] = None

        if action == ACTION_BUY and self._position <= 0:
            trade_info = self._execute_buy(current_price)
        elif action == ACTION_SELL and self._position >= 0:
            trade_info = self._execute_sell(current_price)
        # HOLD → no trade

        self._step_idx += 1
        done = self._step_idx >= min(
            self.raw_data.shape[0] - 1,
            self._step_idx + self.episode_length,
        )

        portfolio_value = self._balance + self._position * current_price
        pnl = portfolio_value - self.initial_balance - self._total_pnl
        self._total_pnl = portfolio_value - self.initial_balance

        reward = self.reward_calc.calculate(
            pnl=pnl,
            action=action,
            portfolio_value=portfolio_value,
            position=self._position,
        )

        info: Dict[str, Any] = {
            "portfolio_value": portfolio_value,
            "balance": self._balance,
            "position": self._position,
            "total_pnl": self._total_pnl,
            "step": self._step_idx,
            "trade": trade_info,
            "reward_metrics": self.reward_calc.get_metrics(),
        }

        next_state = self._get_state() if not done else np.zeros(self.state_dim, dtype=np.float32)
        return next_state, reward, done, info

    def _execute_buy(self, price: float) -> Dict[str, Any]:
        if self._position < 0:
            # close short first
            self._balance += self._position * price
            self._trades.append({"type": "close_short", "price": price, "size": self._position})
            self._position = 0.0

        invest = self._balance * self.position_size
        units = invest / price
        if self._position + units > self.max_position:
            units = max(0.0, self.max_position - self._position)
        if units <= 0:
            return {"type": "buy", "units": 0, "price": price}

        cost = units * price
        self._balance -= cost
        if self._position == 0:
            self._entry_price = price
        else:
            # average entry
            total_units = self._position + units
            self._entry_price = (
                self._entry_price * self._position + price * units
            ) / total_units
        self._position += units
        trade = {"type": "buy", "units": units, "price": price, "cost": cost}
        self._trades.append(trade)
        return trade

    def _execute_sell(self, price: float) -> Dict[str, Any]:
        if self._position > 0:
            # close long
            self._balance += self._position * price
            self._trades.append({"type": "close_long", "price": price, "size": self._position})
            self._position = 0.0

        invest = self._balance * self.position_size
        units = invest / price
        if abs(self._position) + units > self.max_position:
            units = max(0.0, self.max_position - abs(self._position))
        if units <= 0:
            return {"type": "sell", "units": 0, "price": price}

        proceeds = units * price
        self._balance += proceeds
        if self._position == 0:
            self._entry_price = price
        else:
            total_units = abs(self._position) + units
            self._entry_price = (
                self._entry_price * abs(self._position) + price * units
            ) / total_units
        self._position -= units
        trade = {"type": "sell", "units": units, "price": price, "proceeds": proceeds}
        self._trades.append(trade)
        return trade

    @property
    def observation_space_dim(self) -> int:
        return self.state_dim

    @property
    def action_space_n(self) -> int:
        return NUM_ACTIONS


# ── DQN Neural Network ─────────────────────────────────────────────────


class _DQNNetwork:
    """Simple feed-forward Q-network built with PyTorch."""

    def __init__(self, state_dim: int, action_dim: int, hidden_layers: List[int]):
        try:
            import torch
            import torch.nn as nn

            self._torch = torch
            layers: List[nn.Module] = []
            in_dim = state_dim
            for h in hidden_layers:
                layers.append(nn.Linear(in_dim, h))
                layers.append(nn.ReLU())
                in_dim = h
            layers.append(nn.Linear(in_dim, action_dim))
            self.network = nn.Sequential(*layers)
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.network.to(self.device)
        except ImportError:
            raise ImportError("PyTorch is required for DQNAgent. Install with: pip install torch")

    def forward(self, x):
        return self.network(x)

    def parameters(self):
        return self.network.parameters()

    def state_dict(self):
        return self.network.state_dict()

    def load_state_dict(self, d):
        self.network.load_state_dict(d)


# ── DQN Agent ───────────────────────────────────────────────────────────


class DQNAgent:
    """
    Deep Q-Network agent with experience replay and target network.
    """

    def __init__(
        self,
        state_dim: int,
        action_dim: int = NUM_ACTIONS,
        hidden_layers: Optional[List[int]] = None,
        learning_rate: float = 1e-3,
        gamma: float = 0.99,
        epsilon_start: float = 1.0,
        epsilon_end: float = 0.01,
        epsilon_decay: float = 0.995,
        replay_capacity: int = 50_000,
        batch_size: int = 32,
        target_update_freq: int = 10,
    ):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.batch_size = batch_size
        self.target_update_freq = target_update_freq

        hidden = hidden_layers or [128, 64, 32]
        self.q_net = _DQNNetwork(state_dim, action_dim, hidden)
        self.target_net = _DQNNetwork(state_dim, action_dim, hidden)
        self._sync_target()

        self._torch = self.q_net._torch
        self.optimizer = self._torch.optim.Adam(
            list(self.q_net.parameters()), lr=learning_rate
        )
        self.loss_fn = self._torch.nn.MSELoss()
        self.memory: deque = deque(maxlen=replay_capacity)
        self._step_count = 0

    def _sync_target(self):
        self.target_net.network.load_state_dict(self.q_net.network.state_dict())

    def _to_tensor(self, arr):
        return self._torch.FloatTensor(np.asarray(arr)).to(self.q_net.device)

    def select_action(self, state: np.ndarray, greedy: bool = False) -> int:
        if not greedy and random.random() < self.epsilon:
            return random.randint(0, self.action_dim - 1)
        with self._torch.no_grad():
            q = self.q_net.forward(self._to_tensor(state).unsqueeze(0))
            return int(q.argmax(dim=1).item())

    def predict(self, state: np.ndarray) -> int:
        """Greedy action selection (no exploration)."""
        return self.select_action(state, greedy=True)

    def store(self, state, action, reward, next_state, done):
        self.memory.append(Experience(state, action, reward, next_state, done))

    def replay(self, batch_size: Optional[int] = None) -> float:
        """Perform one gradient step from a random mini-batch."""
        bs = batch_size or self.batch_size
        if len(self.memory) < bs:
            return 0.0

        batch = random.sample(self.memory, bs)
        states = self._to_tensor(np.array([e.state for e in batch]))
        actions = self._torch.LongTensor([e.action for e in batch]).unsqueeze(1).to(self.q_net.device)
        rewards = self._torch.FloatTensor([e.reward for e in batch]).unsqueeze(1).to(self.q_net.device)
        next_states = self._to_tensor(np.array([e.next_state for e in batch]))
        dones = self._torch.FloatTensor([float(e.done) for e in batch]).unsqueeze(1).to(self.q_net.device)

        q_vals = self.q_net.forward(states).gather(1, actions)
        with self._torch.no_grad():
            next_q = self.target_net.forward(next_states).max(dim=1, keepdim=True)[0]
            target = rewards + self.gamma * next_q * (1 - dones)

        loss = self.loss_fn(q_vals, target)
        self.optimizer.zero_grad()
        loss.backward()
        self._torch.nn.utils.clip_grad_norm_(self.q_net.parameters(), 10.0)
        self.optimizer.step()

        self._step_count += 1
        if self._step_count % self.target_update_freq == 0:
            self._sync_target()

        return float(loss.item())

    def update_epsilon(self):
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)

    def train(
        self,
        env: TradingEnvironment,
        episodes: int = 1000,
        log_interval: int = 50,
    ) -> Dict[str, Any]:
        """Full training loop."""
        episode_rewards: List[float] = []
        episode_pnls: List[float] = []

        for ep in range(1, episodes + 1):
            state = env.reset()
            total_reward = 0.0
            done = False

            while not done:
                action = self.select_action(state)
                next_state, reward, done, info = env.step(action)
                self.store(state, action, reward, next_state, done)
                loss = self.replay()
                state = next_state
                total_reward += reward

            self.update_epsilon()
            pv = info.get("portfolio_value", env.initial_balance)
            pnl = pv - env.initial_balance
            episode_rewards.append(total_reward)
            episode_pnls.append(pnl)

            if ep % log_interval == 0:
                avg_r = np.mean(episode_rewards[-log_interval:])
                avg_pnl = np.mean(episode_pnls[-log_interval:])
                logger.info(
                    "DQN Ep %d/%d | avg_reward=%.4f | avg_pnl=%.2f | eps=%.4f",
                    ep, episodes, avg_r, avg_pnl, self.epsilon,
                )

        return {
            "episode_rewards": episode_rewards,
            "episode_pnls": episode_pnls,
            "final_epsilon": self.epsilon,
        }

    def save(self, path: Optional[str] = None) -> str:
        path = path or str(SAVED_MODELS_DIR / "dqn_agent.pt")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        payload = {
            "q_net_state": self.q_net.state_dict(),
            "target_net_state": self.target_net.state_dict(),
            "optimizer": self.optimizer.state_dict(),
            "epsilon": self.epsilon,
            "state_dim": self.state_dim,
            "action_dim": self.action_dim,
        }
        self._torch.save(payload, path)
        logger.info("DQN agent saved to %s", path)
        return path

    def load(self, path: Optional[str] = None) -> None:
        path = path or str(SAVED_MODELS_DIR / "dqn_agent.pt")
        payload = self._torch.load(path, map_location=self.q_net.device)
        self.q_net.load_state_dict(payload["q_net_state"])
        self.target_net.load_state_dict(payload["target_net_state"])
        self.optimizer.load_state_dict(payload["optimizer"])
        self.epsilon = payload.get("epsilon", self.epsilon_end)
        logger.info("DQN agent loaded from %s", path)


# ── PPO Neural Networks ─────────────────────────────────────────────────


class _ActorCriticNetwork:
    """Shared-body actor-critic for PPO."""

    def __init__(self, state_dim: int, action_dim: int, hidden_layers: List[int]):
        try:
            import torch
            import torch.nn as nn

            self._torch = torch

            layers: List[nn.Module] = []
            in_dim = state_dim
            for h in hidden_layers:
                layers.append(nn.Linear(in_dim, h))
                layers.append(nn.Tanh())
                in_dim = h
            self.shared = nn.Sequential(*layers)

            self.actor_head = nn.Linear(in_dim, action_dim)
            self.critic_head = nn.Linear(in_dim, 1)

            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.shared.to(self.device)
            self.actor_head.to(self.device)
            self.critic_head.to(self.device)
        except ImportError:
            raise ImportError("PyTorch is required for PPOAgent. Install with: pip install torch")

    def forward(self, x):
        shared_out = self.shared(x)
        logits = self.actor_head(shared_out)
        value = self.critic_head(shared_out)
        return logits, value

    def actor_params(self):
        return list(self.shared.parameters()) + list(self.actor_head.parameters())

    def critic_params(self):
        return list(self.shared.parameters()) + list(self.critic_head.parameters())

    def all_params(self):
        return list(self.shared.parameters()) + list(self.actor_head.parameters()) + list(self.critic_head.parameters())

    def state_dict(self):
        return {
            "shared": self.shared.state_dict(),
            "actor_head": self.actor_head.state_dict(),
            "critic_head": self.critic_head.state_dict(),
        }

    def load_state_dict(self, d):
        self.shared.load_state_dict(d["shared"])
        self.actor_head.load_state_dict(d["actor_head"])
        self.critic_head.load_state_dict(d["critic_head"])


# ── PPO Agent ───────────────────────────────────────────────────────────


class PPOAgent:
    """
    Proximal Policy Optimization agent with Actor-Critic architecture,
    clipped surrogate objective, and GAE.
    """

    def __init__(
        self,
        state_dim: int,
        action_dim: int = NUM_ACTIONS,
        hidden_layers: Optional[List[int]] = None,
        learning_rate: float = 3e-4,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        clip_epsilon: float = 0.2,
        value_coeff: float = 0.5,
        entropy_coeff: float = 0.01,
        ppo_epochs: int = 4,
        rollout_length: int = 2048,
    ):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.clip_epsilon = clip_epsilon
        self.value_coeff = value_coeff
        self.entropy_coeff = entropy_coeff
        self.ppo_epochs = ppo_epochs
        self.rollout_length = rollout_length

        hidden = hidden_layers or [64, 64]
        self.ac = _ActorCriticNetwork(state_dim, action_dim, hidden)
        self._torch = self.ac._torch

        self.actor_optim = self._torch.optim.Adam(self.ac.actor_params(), lr=learning_rate)
        self.critic_optim = self._torch.optim.Adam(self.ac.critic_params(), lr=learning_rate)

        self._rollout_states: List[np.ndarray] = []
        self._rollout_actions: List[int] = []
        self._rollout_rewards: List[float] = []
        self._rollout_values: List[float] = []
        self._rollout_log_probs: List[float] = []
        self._rollout_dones: List[bool] = []

    def _to_tensor(self, arr):
        return self._torch.FloatTensor(np.asarray(arr)).to(self.ac.device)

    def _get_action_value(self, state: np.ndarray) -> Tuple[int, float, float]:
        """Sample action from policy, return (action, log_prob, value)."""
        with self._torch.no_grad():
            logits, value = self.ac.forward(self._to_tensor(state).unsqueeze(0))
            probs = self._torch.softmax(logits, dim=-1)
            dist = self._torch.distributions.Categorical(probs)
            action = dist.sample()
            log_prob = dist.log_prob(action)
        return int(action.item()), float(log_prob.item()), float(value.item())

    def _get_value(self, state: np.ndarray) -> float:
        with self._torch.no_grad():
            _, value = self.ac.forward(self._to_tensor(state).unsqueeze(0))
        return float(value.item())

    def _compute_gae(self, next_value: float) -> List[float]:
        """Generalized Advantage Estimation."""
        advantages: List[float] = []
        gae = 0.0
        values = self._rollout_values + [next_value]
        rewards = self._rollout_rewards
        dones = self._rollout_dones

        for t in reversed(range(len(rewards))):
            delta = rewards[t] + self.gamma * values[t + 1] * (1 - float(dones[t])) - values[t]
            gae = delta + self.gamma * self.gae_lambda * (1 - float(dones[t])) * gae
            advantages.insert(0, gae)
        return advantages

    def _ppo_step(self, advantages: np.ndarray, returns: np.ndarray) -> Dict[str, float]:
        """PPO update for one batch of rollout data."""
        states = self._torch.FloatTensor(np.array(self._rollout_states)).to(self.ac.device)
        actions = self._torch.LongTensor(self._rollout_actions).unsqueeze(1).to(self.ac.device)
        old_log_probs = self._torch.FloatTensor(self._rollout_log_probs).unsqueeze(1).to(self.ac.device)

        advantages_t = self._torch.FloatTensor(advantages).unsqueeze(1).to(self.ac.device)
        returns_t = self._torch.FloatTensor(returns).unsqueeze(1).to(self.ac.device)

        total_policy_loss = 0.0
        total_value_loss = 0.0
        total_entropy = 0.0

        for _ in range(self.ppo_epochs):
            logits, values = self.ac.forward(states)
            probs = self._torch.softmax(logits, dim=-1)
            dist = self._torch.distributions.Categorical(probs)
            new_log_probs = dist.log_prob(actions.squeeze(1)).unsqueeze(1)
            entropy = dist.entropy().mean()

            # Clipped surrogate
            ratio = self._torch.exp(new_log_probs - old_log_probs)
            surr1 = ratio * advantages_t
            surr2 = self._torch.clamp(ratio, 1 - self.clip_epsilon, 1 + self.clip_epsilon) * advantages_t
            policy_loss = -self._torch.min(surr1, surr2).mean()

            value_loss = self._torch.nn.functional.mse_loss(values, returns_t)

            # Update actor
            self.actor_optim.zero_grad()
            (policy_loss - self.entropy_coeff * entropy).backward()
            self._torch.nn.utils.clip_grad_norm_(self.ac.actor_params(), 0.5)
            self.actor_optim.step()

            # Update critic
            self.critic_optim.zero_grad()
            (self.value_coeff * value_loss).backward()
            self._torch.nn.utils.clip_grad_norm_(self.ac.critic_params(), 0.5)
            self.critic_optim.step()

            total_policy_loss += float(policy_loss.item())
            total_value_loss += float(value_loss.item())
            total_entropy += float(entropy.item())

        n = self.ppo_epochs
        return {
            "policy_loss": total_policy_loss / n,
            "value_loss": total_value_loss / n,
            "entropy": total_entropy / n,
        }

    def predict(self, state: np.ndarray) -> int:
        """Greedy action selection."""
        with self._torch.no_grad():
            logits, _ = self.ac.forward(self._to_tensor(state).unsqueeze(0))
            return int(logits.argmax(dim=1).item())

    def select_action(self, state: np.ndarray) -> int:
        """Stochastic action selection (for training)."""
        action, _, _ = self._get_action_value(state)
        return action

    def _clear_rollout(self):
        self._rollout_states.clear()
        self._rollout_actions.clear()
        self._rollout_rewards.clear()
        self._rollout_values.clear()
        self._rollout_log_probs.clear()
        self._rollout_dones.clear()

    def train(
        self,
        env: TradingEnvironment,
        episodes: int = 500,
        log_interval: int = 50,
    ) -> Dict[str, Any]:
        """Full PPO training loop."""
        episode_rewards: List[float] = []
        episode_pnls: List[float] = []
        update_count = 0

        for ep in range(1, episodes + 1):
            state = env.reset()
            total_reward = 0.0
            done = False
            self._clear_rollout()

            # Collect rollout
            while not done:
                action, log_prob, value = self._get_action_value(state)
                next_state, reward, done, info = env.step(action)

                self._rollout_states.append(state)
                self._rollout_actions.append(action)
                self._rollout_rewards.append(reward)
                self._rollout_values.append(value)
                self._rollout_log_probs.append(log_prob)
                self._rollout_dones.append(done)

                state = next_state
                total_reward += reward

                # Update when rollout is full
                if len(self._rollout_states) >= self.rollout_length and not done:
                    next_val = self._get_value(state)
                    advantages = self._compute_gae(next_val)
                    advantages = np.array(advantages, dtype=np.float32)
                    returns = advantages + np.array(self._rollout_values, dtype=np.float32)
                    # Normalise
                    if len(advantages) > 1:
                        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
                    self._ppo_step(advantages, returns)
                    self._clear_rollout()
                    update_count += 1

            # End of episode update if rollout not empty
            if self._rollout_states:
                next_val = 0.0 if done else self._get_value(state)
                advantages = self._compute_gae(next_val)
                advantages = np.array(advantages, dtype=np.float32)
                returns = advantages + np.array(self._rollout_values, dtype=np.float32)
                if len(advantages) > 1:
                    advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
                self._ppo_step(advantages, returns)
                self._clear_rollout()
                update_count += 1

            pv = info.get("portfolio_value", env.initial_balance)
            pnl = pv - env.initial_balance
            episode_rewards.append(total_reward)
            episode_pnls.append(pnl)

            if ep % log_interval == 0:
                avg_r = np.mean(episode_rewards[-log_interval:])
                avg_pnl = np.mean(episode_pnls[-log_interval:])
                logger.info(
                    "PPO Ep %d/%d | avg_reward=%.4f | avg_pnl=%.2f | updates=%d",
                    ep, episodes, avg_r, avg_pnl, update_count,
                )

        return {
            "episode_rewards": episode_rewards,
            "episode_pnls": episode_pnls,
            "total_updates": update_count,
        }

    def save(self, path: Optional[str] = None) -> str:
        path = path or str(SAVED_MODELS_DIR / "ppo_agent.pt")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        payload = {
            "ac_state": self.ac.state_dict(),
            "actor_optim": self.actor_optim.state_dict(),
            "critic_optim": self.critic_optim.state_dict(),
            "state_dim": self.state_dim,
            "action_dim": self.action_dim,
        }
        self._torch.save(payload, path)
        logger.info("PPO agent saved to %s", path)
        return path

    def load(self, path: Optional[str] = None) -> None:
        path = path or str(SAVED_MODELS_DIR / "ppo_agent.pt")
        payload = self._torch.load(path, map_location=self.ac.device)
        self.ac.load_state_dict(payload["ac_state"])
        self.actor_optim.load_state_dict(payload["actor_optim"])
        self.critic_optim.load_state_dict(payload["critic_optim"])
        logger.info("PPO agent loaded from %s", path)


# ── RL Trainer ──────────────────────────────────────────────────────────


@dataclass
class RLTrainResult:
    """Container for training + evaluation results."""
    model_type: str
    train_metrics: Dict[str, Any]
    test_metrics: Dict[str, Any]
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    total_return: float = 0.0
    model_path: str = ""


class RLTrainer:
    """
    Walk-forward RL training with train/test splits,
    performance metrics, and DQN vs PPO comparison.
    """

    def __init__(
        self,
        train_ratio: float = 0.8,
        episode_length: int = 500,
        reward_config: Optional[Dict[str, Any]] = None,
    ):
        self.train_ratio = train_ratio
        self.episode_length = episode_length
        self.reward_config = reward_config or {}

    def _split_data(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        split = int(data.shape[0] * self.train_ratio)
        return data[:split], data[split:]

    def _evaluate_agent(
        self,
        agent,
        data: np.ndarray,
        n_episodes: int = 10,
    ) -> Dict[str, float]:
        """Run n evaluation episodes and compute aggregate metrics."""
        env = TradingEnvironment(
            data=data,
            episode_length=self.episode_length,
            reward_config=self.reward_config,
        )
        returns: List[float] = []
        pnls: List[float] = []
        all_trades: List[Dict[str, Any]] = []

        for _ in range(n_episodes):
            state = env.reset()
            done = False
            while not done:
                action = agent.predict(state)
                state, _, done, info = env.step(action)
            pv = info.get("portfolio_value", env.initial_balance)
            pnl = pv - env.initial_balance
            pnls.append(pnl)
            returns.append(pnl / env.initial_balance)
            all_trades.extend(env._trades)

        wins = sum(1 for p in pnls if p > 0)
        total_trades = len(all_trades)

        ret_arr = np.array(returns)
        sharpe = 0.0
        if len(ret_arr) > 1 and ret_arr.std() > 1e-10:
            sharpe = (ret_arr.mean() - 0.02 / 252) / ret_arr.std() * np.sqrt(252)

        running_max = np.maximum.accumulate(pnls)
        drawdowns = (running_max - pnls) / np.where(running_max > 0, running_max, 1)
        max_dd = float(drawdowns.max()) if len(drawdowns) > 0 else 0.0

        return {
            "sharpe_ratio": float(sharpe),
            "max_drawdown": max_dd,
            "win_rate": wins / max(len(pnls), 1),
            "total_return": float(np.mean(returns)),
            "avg_pnl": float(np.mean(pnls)),
            "std_pnl": float(np.std(pnls)),
            "total_trades": total_trades,
            "n_episodes": n_episodes,
        }

    def _make_dqn(self, state_dim: int) -> DQNAgent:
        return DQNAgent(state_dim=state_dim, action_dim=NUM_ACTIONS)

    def _make_ppo(self, state_dim: int) -> PPOAgent:
        return PPOAgent(state_dim=state_dim, action_dim=NUM_ACTIONS)

    def train_and_evaluate(
        self,
        symbol: str,
        data: np.ndarray,
        episodes: int = 1000,
        eval_episodes: int = 10,
        train_dqn: bool = True,
        train_ppo: bool = True,
    ) -> Dict[str, RLTrainResult]:
        """
        Full walk-forward training pipeline.

        Args:
            symbol: ticker symbol (used for logging/saving).
            data: full OHLCV+indicator dataset.
            episodes: training episodes.
            eval_episodes: episodes for evaluation.
            train_dqn: whether to train DQN.
            train_ppo: whether to train PPO.

        Returns:
            dict mapping 'dqn' and/or 'ppo' to RLTrainResult.
        """
        train_data, test_data = self._split_data(data)
        logger.info(
            "Walk-forward split for %s: train=%d test=%d",
            symbol, train_data.shape[0], test_data.shape[0],
        )

        results: Dict[str, RLTrainResult] = {}

        if train_dqn:
            logger.info("Training DQN for %s ...", symbol)
            t0 = time.time()
            env = TradingEnvironment(
                data=train_data,
                episode_length=self.episode_length,
                reward_config=self.reward_config,
            )
            dqn = self._make_dqn(env.observation_space_dim)
            train_metrics = dqn.train(env, episodes=episodes)
            train_time = time.time() - t0

            test_metrics = self._evaluate_agent(dqn, test_data, n_episodes=eval_episodes)
            save_path = str(SAVED_MODELS_DIR / f"dqn_{symbol}.pt")
            dqn.save(save_path)

            results["dqn"] = RLTrainResult(
                model_type="DQN",
                train_metrics={**train_metrics, "train_time_s": train_time},
                test_metrics=test_metrics,
                sharpe_ratio=test_metrics["sharpe_ratio"],
                max_drawdown=test_metrics["max_drawdown"],
                win_rate=test_metrics["win_rate"],
                total_return=test_metrics["total_return"],
                model_path=save_path,
            )
            logger.info("DQN done: Sharpe=%.3f MaxDD=%.3f WR=%.3f",
                        test_metrics["sharpe_ratio"], test_metrics["max_drawdown"], test_metrics["win_rate"])

        if train_ppo:
            logger.info("Training PPO for %s ...", symbol)
            t0 = time.time()
            env = TradingEnvironment(
                data=train_data,
                episode_length=self.episode_length,
                reward_config=self.reward_config,
            )
            ppo = self._make_ppo(env.observation_space_dim)
            train_metrics = ppo.train(env, episodes=episodes)
            train_time = time.time() - t0

            test_metrics = self._evaluate_agent(ppo, test_data, n_episodes=eval_episodes)
            save_path = str(SAVED_MODELS_DIR / f"ppo_{symbol}.pt")
            ppo.save(save_path)

            results["ppo"] = RLTrainResult(
                model_type="PPO",
                train_metrics={**train_metrics, "train_time_s": train_time},
                test_metrics=test_metrics,
                sharpe_ratio=test_metrics["sharpe_ratio"],
                max_drawdown=test_metrics["max_drawdown"],
                win_rate=test_metrics["win_rate"],
                total_return=test_metrics["total_return"],
                model_path=save_path,
            )
            logger.info("PPO done: Sharpe=%.3f MaxDD=%.3f WR=%.3f",
                        test_metrics["sharpe_ratio"], test_metrics["max_drawdown"], test_metrics["win_rate"])

        # Comparison
        if len(results) == 2:
            winner = max(results, key=lambda k: results[k].sharpe_ratio)
            logger.info(
                "Model comparison for %s: DQN Sharpe=%.3f vs PPO Sharpe=%.3f → winner=%s",
                symbol,
                results["dqn"].sharpe_ratio,
                results["ppo"].sharpe_ratio,
                winner.upper(),
            )

        return results

    def compare_models(
        self,
        results: Dict[str, RLTrainResult],
    ) -> Dict[str, Any]:
        """Return a comparison summary dict."""
        comparison: Dict[str, Any] = {}
        for key, r in results.items():
            comparison[key] = {
                "model_type": r.model_type,
                "sharpe_ratio": r.sharpe_ratio,
                "max_drawdown": r.max_drawdown,
                "win_rate": r.win_rate,
                "total_return": r.total_return,
                "model_path": r.model_path,
            }
        if len(results) >= 2:
            best = max(results.values(), key=lambda x: x.sharpe_ratio)
            comparison["best_model"] = best.model_type
        return comparison
