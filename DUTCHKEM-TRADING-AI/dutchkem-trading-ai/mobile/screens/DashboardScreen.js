import React, { useEffect } from 'react';
import { View, ScrollView, StyleSheet, ActivityIndicator } from 'react-native';
import { Card, Text, ProgressBar, Surface, Avatar } from 'react-native-paper';
import { useDispatch, useSelector } from 'react-redux';
import { fetchPortfolio, fetchPositions, fetchActiveSignals, fetchRiskDashboard } from '../store';

const DashboardScreen = () => {
  const dispatch = useDispatch();
  const { portfolio, positions, loading: tradingLoading } = useSelector((s) => s.trading);
  const { activeSignals } = useSelector((s) => s.signals);
  const { dashboard } = useSelector((s) => s.risk);
  const { user } = useSelector((s) => s.auth);

  useEffect(() => {
    dispatch(fetchPortfolio());
    dispatch(fetchPositions());
    dispatch(fetchActiveSignals());
    dispatch(fetchRiskDashboard());
  }, [dispatch]);

  if (tradingLoading && !portfolio) {
    return <View style={styles.container}><ActivityIndicator size="large" color="#1976d2" /></View>;
  }

  const balance = portfolio?.balance || 0;
  const equity = portfolio?.equity || 0;
  const drawdown = dashboard?.current_status?.drawdown_percent || 0;
  const dailyLoss = dashboard?.current_status?.daily_pnl_percent || 0;
  const riskParams = dashboard?.risk_parameters || {};

  return (
    <ScrollView style={styles.container}>
      <Surface style={styles.header}>
        <Avatar.Text size={50} label={(user?.first_name?.[0] || 'U') + (user?.last_name?.[0] || '')} style={styles.avatar} />
        <View>
          <Text style={styles.greeting}>Good Morning,</Text>
          <Text style={styles.name}>{user?.first_name || 'Trader'}</Text>
        </View>
      </Surface>

      <View style={styles.cardRow}>
        <Card style={styles.card}>
          <Card.Content>
            <Text style={styles.cardLabel}>Balance</Text>
            <Text style={styles.cardValue}>${Number(balance).toLocaleString()}</Text>
          </Card.Content>
        </Card>
        <Card style={styles.card}>
          <Card.Content>
            <Text style={styles.cardLabel}>Equity</Text>
            <Text style={styles.cardValue}>${Number(equity).toLocaleString()}</Text>
          </Card.Content>
        </Card>
      </View>

      <Card style={styles.fullCard}>
        <Card.Content>
          <Text style={styles.cardLabel}>Risk Status</Text>
          <View style={styles.riskRow}>
            <Text style={styles.riskText}>Daily Loss</Text>
            <Text style={styles.riskText}>{Math.abs(dailyLoss).toFixed(2)}% / {riskParams.max_daily_loss || 2}%</Text>
          </View>
          <ProgressBar progress={Math.min(Math.abs(dailyLoss) / (riskParams.max_daily_loss || 2), 1)} color="#4caf50" style={styles.progress} />
          <View style={styles.riskRow}>
            <Text style={styles.riskText}>Drawdown</Text>
            <Text style={styles.riskText}>{drawdown.toFixed(2)}% / {riskParams.max_drawdown || 15}%</Text>
          </View>
          <ProgressBar progress={Math.min(drawdown / (riskParams.max_drawdown || 15), 1)} color="#1976d2" style={styles.progress} />
        </Card.Content>
      </Card>

      <Card style={styles.fullCard}>
        <Card.Content>
          <Text style={styles.cardLabel}>Active Signals ({activeSignals.length})</Text>
          {activeSignals.length === 0 ? (
            <Text style={styles.emptyText}>No active signals</Text>
          ) : activeSignals.slice(0, 5).map((signal, idx) => (
            <View key={signal.id || idx} style={styles.signalItem}>
              <Text style={styles.signalSymbol}>{signal.symbol?.name || signal.symbol}</Text>
              <Text style={[styles.signalDir, { color: signal.signal_type === 'BUY' ? '#4caf50' : '#f44336' }]}>
                {signal.signal_type} {signal.strength || 0}%
              </Text>
            </View>
          ))}
        </Card.Content>
      </Card>

      <Card style={styles.fullCard}>
        <Card.Content>
          <Text style={styles.cardLabel}>Open Positions ({positions.length})</Text>
          {positions.length === 0 ? (
            <Text style={styles.emptyText}>No open positions</Text>
          ) : positions.slice(0, 5).map((pos, idx) => (
            <View key={pos.id || idx} style={styles.signalItem}>
              <Text style={styles.signalSymbol}>{pos.symbol?.name || pos.symbol}</Text>
              <Text style={[styles.signalDir, { color: parseFloat(pos.unrealized_pnl) >= 0 ? '#4caf50' : '#f44336' }]}>
                {pos.position_type} ${Number(pos.unrealized_pnl).toFixed(2)}
              </Text>
            </View>
          ))}
        </Card.Content>
      </Card>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0a1929' },
  header: { flexDirection: 'row', alignItems: 'center', padding: 20, backgroundColor: '#1a2940' },
  avatar: { backgroundColor: '#1976d2', marginRight: 15 },
  greeting: { color: '#888', fontSize: 14 },
  name: { color: '#fff', fontSize: 20, fontWeight: 'bold' },
  cardRow: { flexDirection: 'row', justifyContent: 'space-between', padding: 10 },
  card: { flex: 1, margin: 5, backgroundColor: '#1a2940' },
  fullCard: { margin: 10, backgroundColor: '#1a2940' },
  cardLabel: { color: '#888', fontSize: 12 },
  cardValue: { color: '#fff', fontSize: 24, fontWeight: 'bold' },
  progress: { marginTop: 10, height: 8, borderRadius: 4 },
  riskRow: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 10 },
  riskText: { color: '#fff', fontSize: 14 },
  signalItem: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#333' },
  signalSymbol: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
  signalDir: { fontSize: 14, fontWeight: 'bold' },
  emptyText: { color: '#888', textAlign: 'center', padding: 20 },
});

export default DashboardScreen;
