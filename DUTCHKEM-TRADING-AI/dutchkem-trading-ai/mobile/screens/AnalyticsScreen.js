import React, { useEffect, useState } from 'react';
import { View, ScrollView, StyleSheet, Dimensions, ActivityIndicator } from 'react-native';
import { Card, Text, Surface } from 'react-native-paper';
import { LineChart, BarChart } from 'react-native-chart-kit';
import { useDispatch, useSelector } from 'react-redux';
import { fetchPerformance } from '../store';

const screenWidth = Dimensions.get('window').width;

const AnalyticsScreen = () => {
  const dispatch = useDispatch();
  const { performance, loading } = useSelector((s) => s.analytics);
  const [period, setPeriod] = useState('week');

  useEffect(() => { dispatch(fetchPerformance()); }, [dispatch]);

  const chartConfig = {
    backgroundColor: '#1a2940',
    backgroundGradientFrom: '#1a2940',
    backgroundGradientTo: '#0a1929',
    decimalPlaces: 0,
    color: (opacity = 1) => `rgba(25, 118, 210, ${opacity})`,
    labelColor: (opacity = 1) => `rgba(136, 136, 136, ${opacity})`,
    style: { borderRadius: 16 },
    propsForDots: { r: '4', strokeWidth: '2', stroke: '#1976d2' },
  };

  const currentPeriod = performance?.[period] || {};
  const dailyPnl = performance?.daily_pnl || [];
  const symbolBreakdown = performance?.symbol_breakdown || {};

  return (
    <ScrollView style={styles.container}>
      <Surface style={styles.header}>
        <Text style={styles.title}>Analytics</Text>
      </Surface>

      <View style={styles.periodRow}>
        {['today', 'week', 'month'].map((p) => (
          <Card key={p} style={[styles.periodCard, period === p && styles.periodActive]}
            onPress={() => setPeriod(p)}>
            <Card.Content>
              <Text style={styles.periodLabel}>{p.charAt(0).toUpperCase() + p.slice(1)}</Text>
              <Text style={[styles.periodValue, { color: (currentPeriod.total_pnl || 0) >= 0 ? '#4caf50' : '#f44336' }]}>
                ${currentPeriod.total_pnl || 0}
              </Text>
            </Card.Content>
          </Card>
        ))}
      </View>

      {loading ? (
        <ActivityIndicator size="large" color="#1976d2" style={{ marginTop: 40 }} />
      ) : (
        <>
          <Card style={styles.chartCard}>
            <Card.Content>
              <Text style={styles.chartTitle}>Daily P&L</Text>
              {dailyPnl.length > 0 ? (
                <LineChart
                  data={{
                    labels: dailyPnl.slice(-7).map((d) => d.date?.slice(5) || ''),
                    datasets: [{ data: dailyPnl.slice(-7).map((d) => d.pnl || 0) }],
                  }}
                  width={screenWidth - 60} height={200}
                  chartConfig={chartConfig} bezier style={styles.chart}
                />
              ) : (
                <Text style={styles.emptyText}>No data available</Text>
              )}
            </Card.Content>
          </Card>

          <Card style={styles.chartCard}>
            <Card.Content>
              <Text style={styles.chartTitle}>P&L by Symbol</Text>
              {Object.keys(symbolBreakdown).length > 0 ? (
                <BarChart
                  data={{
                    labels: Object.keys(symbolBreakdown),
                    datasets: [{ data: Object.values(symbolBreakdown).map((s) => s.pnl || 0) }],
                  }}
                  width={screenWidth - 60} height={200}
                  chartConfig={chartConfig} style={styles.chart}
                />
              ) : (
                <Text style={styles.emptyText}>No data available</Text>
              )}
            </Card.Content>
          </Card>

          <Card style={styles.card}>
            <Card.Content>
              <Text style={styles.chartTitle}>Performance Summary</Text>
              <View style={styles.summaryRow}>
                <View style={styles.summaryItem}>
                  <Text style={styles.label}>Total Trades</Text>
                  <Text style={styles.value}>{currentPeriod.total_trades || 0}</Text>
                </View>
                <View style={styles.summaryItem}>
                  <Text style={styles.label}>Win Rate</Text>
                  <Text style={styles.value}>{currentPeriod.win_rate || 0}%</Text>
                </View>
                <View style={styles.summaryItem}>
                  <Text style={styles.label}>Profit Factor</Text>
                  <Text style={styles.value}>{currentPeriod.profit_factor || 0}</Text>
                </View>
              </View>
            </Card.Content>
          </Card>
        </>
      )}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0a1929' },
  header: { padding: 20, backgroundColor: '#1a2940' },
  title: { color: '#fff', fontSize: 24, fontWeight: 'bold' },
  periodRow: { flexDirection: 'row', justifyContent: 'space-between', padding: 10 },
  periodCard: { flex: 1, margin: 5, backgroundColor: '#1a2940' },
  periodActive: { borderColor: '#1976d2', borderWidth: 2 },
  periodLabel: { color: '#888', fontSize: 12 },
  periodValue: { color: '#fff', fontSize: 18, fontWeight: 'bold' },
  chartCard: { margin: 10, backgroundColor: '#1a2940' },
  card: { margin: 10, backgroundColor: '#1a2940' },
  chartTitle: { color: '#fff', fontSize: 16, fontWeight: 'bold', marginBottom: 10 },
  chart: { borderRadius: 16 },
  label: { color: '#888', fontSize: 12 },
  value: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
  summaryRow: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 10 },
  summaryItem: { alignItems: 'center' },
  emptyText: { color: '#888', textAlign: 'center', padding: 20 },
});

export default AnalyticsScreen;
