import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Symbol(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=20, unique=True)
    description = models.CharField(max_length=100)
    category = models.CharField(
        max_length=20,
        choices=[
            ("MAJOR", "Major"),
            ("MINOR", "Minor"),
            ("EXOTIC", "Exotic"),
            ("COMMODITY", "Commodity"),
            ("CRYPTO", "Crypto"),
            ("INDEX", "Index"),
        ],
    )
    base_currency = models.CharField(max_length=3)
    quote_currency = models.CharField(max_length=3)
    pip_size = models.DecimalField(max_digits=10, decimal_places=6, default=0.0001)
    spread = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    contract_size = models.DecimalField(max_digits=10, decimal_places=2, default=100000)
    margin_requirement = models.DecimalField(max_digits=5, decimal_places=2, default=0.01)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Multi-timeframe support
    supported_timeframes = models.ManyToManyField("indicators.Timeframe", blank=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return self.name


class Trade(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trades")
    symbol = models.ForeignKey(Symbol, on_delete=models.PROTECT, related_name="trades")
    timeframe = models.ForeignKey("indicators.Timeframe", on_delete=models.SET_NULL, null=True, related_name="trades")

    position_type = models.CharField(
        max_length=4,
        choices=[
            ("BUY", "Buy"),
            ("SELL", "Sell"),
        ],
    )
    volume = models.DecimalField(max_digits=10, decimal_places=2)
    open_price = models.DecimalField(max_digits=20, decimal_places=6)
    close_price = models.DecimalField(max_digits=20, decimal_places=6, blank=True, null=True)

    stop_loss = models.DecimalField(max_digits=20, decimal_places=6, blank=True, null=True)
    take_profit = models.DecimalField(max_digits=20, decimal_places=6, blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ("PENDING", "Pending"),
            ("OPEN", "Open"),
            ("CLOSED", "Closed"),
            ("CANCELLED", "Cancelled"),
            ("REJECTED", "Rejected"),
        ],
        default="PENDING",
    )

    profit_loss = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    swap = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    mt5_ticket = models.CharField(max_length=50, blank=True, null=True)
    signal = models.ForeignKey("signals.Signal", on_delete=models.SET_NULL, blank=True, null=True)
    expert_advisor = models.ForeignKey(
        "expert_advisors.ExpertAdvisor", on_delete=models.SET_NULL, blank=True, null=True
    )

    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-opened_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["symbol", "status"]),
            models.Index(fields=["opened_at"]),
        ]

    def __str__(self):
        return f"{self.position_type} {self.volume} {self.symbol.name} @ {self.open_price}"

    @property
    def duration(self):
        if self.closed_at:
            return self.closed_at - self.opened_at
        return timezone.now() - self.opened_at


class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    symbol = models.ForeignKey(Symbol, on_delete=models.PROTECT, related_name="orders")
    timeframe = models.ForeignKey("indicators.Timeframe", on_delete=models.SET_NULL, null=True, related_name="orders")

    order_type = models.CharField(
        max_length=20,
        choices=[
            ("MARKET", "Market"),
            ("LIMIT", "Limit"),
            ("STOP", "Stop"),
            ("STOP_LIMIT", "Stop Limit"),
        ],
    )
    position_type = models.CharField(
        max_length=4,
        choices=[
            ("BUY", "Buy"),
            ("SELL", "Sell"),
        ],
    )
    volume = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=20, decimal_places=6)

    stop_loss = models.DecimalField(max_digits=20, decimal_places=6, blank=True, null=True)
    take_profit = models.DecimalField(max_digits=20, decimal_places=6, blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ("PENDING", "Pending"),
            ("FILLED", "Filled"),
            ("PARTIALLY_FILLED", "Partially Filled"),
            ("CANCELLED", "Cancelled"),
            ("EXPIRED", "Expired"),
        ],
        default="PENDING",
    )

    risk_amount = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    risk_reward_ratio = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    mt5_ticket = models.CharField(max_length=50, blank=True, null=True)
    signal = models.ForeignKey("signals.Signal", on_delete=models.SET_NULL, blank=True, null=True)
    expiration = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.order_type} {self.position_type} {self.volume} {self.symbol.name}"


class Position(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="positions")
    symbol = models.ForeignKey(Symbol, on_delete=models.PROTECT, related_name="positions")
    trade = models.OneToOneField(Trade, on_delete=models.CASCADE, related_name="position")
    timeframe = models.ForeignKey(
        "indicators.Timeframe", on_delete=models.SET_NULL, null=True, related_name="positions"
    )

    position_type = models.CharField(
        max_length=4,
        choices=[
            ("BUY", "Buy"),
            ("SELL", "Sell"),
        ],
    )
    volume = models.DecimalField(max_digits=10, decimal_places=2)
    open_price = models.DecimalField(max_digits=20, decimal_places=6)
    current_price = models.DecimalField(max_digits=20, decimal_places=6)

    stop_loss = models.DecimalField(max_digits=20, decimal_places=6, blank=True, null=True)
    take_profit = models.DecimalField(max_digits=20, decimal_places=6, blank=True, null=True)

    unrealized_pnl = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    margin_used = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    opened_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-opened_at"]

    def __str__(self):
        return f"{self.position_type} {self.volume} {self.symbol.name}"

    def calculate_unrealized_pnl(self):
        if self.position_type == "BUY":
            pnl = (self.current_price - self.open_price) * self.volume * self.symbol.contract_size
        else:
            pnl = (self.open_price - self.current_price) * self.volume * self.symbol.contract_size
        self.unrealized_pnl = pnl
        self.save()
        return pnl
