from rest_framework import serializers

from .models import (
    Indicator,
    IndicatorCategory,
    IndicatorValue,
    Timeframe,
    TimeframeIndicatorConfig,
)


class TimeframeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Timeframe
        fields = [
            "id",
            "code",
            "name",
            "minutes",
            "strategy_type",
            "risk_level",
            "target_pips_min",
            "target_pips_max",
            "stop_loss_min",
            "stop_loss_max",
            "win_rate_target_min",
            "win_rate_target_max",
            "risk_reward_ratio",
            "is_active",
        ]


class IndicatorCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = IndicatorCategory
        fields = ["id", "name", "description", "icon"]


class IndicatorSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    suitable_timeframe_codes = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="code", source="suitable_timeframes"
    )

    class Meta:
        model = Indicator
        fields = [
            "id",
            "name",
            "display_name",
            "category",
            "category_name",
            "indicator_type",
            "description",
            "formula",
            "default_parameters",
            "is_active",
            "suitable_timeframe_codes",
        ]


class IndicatorValueSerializer(serializers.ModelSerializer):
    symbol_name = serializers.CharField(source="symbol.name", read_only=True)
    indicator_name = serializers.CharField(source="indicator.display_name", read_only=True)
    timeframe_code = serializers.CharField(source="timeframe.code", read_only=True)

    class Meta:
        model = IndicatorValue
        fields = [
            "id",
            "symbol",
            "symbol_name",
            "indicator",
            "indicator_name",
            "timeframe",
            "timeframe_code",
            "timestamp",
            "value",
            "signal",
        ]


class TimeframeIndicatorConfigSerializer(serializers.ModelSerializer):
    indicator_name = serializers.CharField(source="indicator.display_name", read_only=True)
    timeframe_code = serializers.CharField(source="timeframe.code", read_only=True)

    class Meta:
        model = TimeframeIndicatorConfig
        fields = [
            "id",
            "timeframe",
            "timeframe_code",
            "indicator",
            "indicator_name",
            "weight",
            "parameters",
            "priority",
        ]
