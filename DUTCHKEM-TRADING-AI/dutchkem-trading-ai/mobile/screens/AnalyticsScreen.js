import React, { useState, useEffect } from 'react';
import { View, ScrollView, StyleSheet, Dimensions } from 'react-native';
import { Card, Text, Surface, SegmentedControl } from 'react-native-paper';
import { LineChart, BarChart } from 'react-native-chart-kit';

const screenWidth = Dimensions.get('window').width;

const AnalyticsScreen = () => {
  const [period, setPeriod] = useState('Week');

  const performance = {
    today: { pnl: 130, trades: 8, winRate: 62.5 },
    week: { pnl: 890, trades: 45, winRate: 58.3 },
    month: { pnl: 3200, trades: 180, winRate: 55.6 },
  };

  const dailyPnl = [120, -80, 250, 180, -50, 320, 150];
  const labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  const symbolData = [
    { symbol: 'EURUSD', pnl: 450, trades: 25, wins: 15 },
    { symbol: 'GBPUSD', pnl: 320, trades: 18, wins: 10 },
    { symbol: 'USDJPY', pnl: 120, trades: 12, wins: 7 },
  ];

  return (
    <ScrollView style={styles.container}>
      <Surface style={styles.header}>
        <Text style={styles.title}>Analytics</Text>
      </Surface>

      <SegmentedControl
        values={['Day', 'Week', 'Month']}
        selectedIndex={['Day', 'Week', 'Month'].indexOf(period)}
        onValueChange={(i) => setPeriod(['Day', 'Week', 'Month'][i])}
        style={styles.segmented}
      />

      <View style={styles.cardRow}>
        <Card style={styles.card}>
          <Card.Content>
            <Text style={styles.label}>P&L</Text>
            <Text style={[styles.value, { color: performance[period.toLowerCase()].pnl >= 0 ? '#4caf50' : '#f44336' }]}>
              ${performance[period.toLowerCase()].pnl}
            </Text>
          </Card.Content>
        </Card>
        <Card style={styles.card}>
          <Card.Content>
            <Text style={styles.label}>Trades</Text>
            <Text style={styles.value}>{performance[period.toLowerCase()].trades}</Text>
          </Card.Content>
        </Card>
        <Card style={styles.card}>
          <Card.Content>
            <Text style={styles.label}>Win Rate</Text>
            <Text style={styles.value}>{performance[period.toLowerCase()].winRate}%</Text>
          </Card.Content>
        </Card>
      </View>

      <Card style={styles.chartCard}>
        <Card.Content>
          <Text style={styles.chartTitle}>Daily P&L</Text>
          <LineChart
            data={{
              labels: labels,
              datasets: [{ data: dailyPnl }],
            }}
            width={screenWidth - 60}
            height={200}
            chartConfig={{
              backgroundColor: '#1a2940',
              backgroundGradientFrom: '#1a2940',
              backgroundGradientTo: '#0a1929',
              decimalPlaces: 0,
              color: (opacity = 1) => `rgba(25, 118, 210, ${opacity})`,
              labelColor: (opacity = 1) => `rgba(136, 136, 136, ${opacity})`,
              style: { borderRadius: 16 },
              propsForDots: { r: '4', strokeWidth: '2', stroke: '#1976d2' },
            }}
            bezier
            style={styles.chart}
          />
        </Card.Content>
      </Card>

      <Card style={styles.chartCard}>
        <Card.Content>
          <Text style={styles.chartTitle}>P&L by Symbol</Text>
          <BarChart
            data={{
              labels: symbolData.map(s => s.symbol),
              datasets: [{ data: symbolData.map(s => s.pnl) }],
            }}
            width={screenWidth - 60}
            height={200}
            chartConfig={{
              backgroundColor: '#1a2940',
              backgroundGradientFrom: '#1a2940',
              backgroundGradientTo: '#0a1929',
              decimalPlaces: 0,
              color: (opacity = 1) => `rgba(25, 118, 210, ${opacity})`,
              labelColor: (opacity = 1) => `rgba(136, 136, 136, ${opacity})`,
              barPercentage: 0.6,
            }}
            style={styles.chart}
          />
        </Card.Content>
      </Card>

      <Card style={styles.card}>
        <Card.Content>
          <Text style={styles.chartTitle}>Symbol Breakdown</Text>
          {symbolData.map((s) => (
            <View key={s.symbol} style={styles.symbolRow}>
              <View>
                <Text style={styles.symbolName}>{s.symbol}</Text>
                <Text style={styles.symbolTrades}>{s.trades} trades</Text>
              </View>
              <Text style={[styles.symbolPnl, { color: s.pnl >= 0 ? '#4caf50' : '#f44336' }]}>
                ${s.pnl}
              </Text>
            </View>
          ))}
        </Card.Content>
      </Card>

      <Card style={styles.card}>
        <Card.Content>
          <Text style={styles.chartTitle}>Risk Status</Text>
          <View style={styles.riskRow}>
            <Text style={styles.riskLabel}>Daily Loss Remaining</Text>
            <Text style={styles.riskValue}>1.5%</Text>
          </View>
          <View style={styles.riskRow}>
            <Text style={styles.riskLabel}>Drawdown Remaining</Text>
            <Text style={styles.riskValue}>13.8%</Text>
          </View>
          <View style={styles.riskRow}>
            <Text style={styles.riskLabel}>Daily Trades</Text>
            <Text style={styles.riskValue}>3 / 10</Text>
          </View>
        </Card.Content>
      </Card>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0a1929',
  },
  header: {
    padding: 20,
    backgroundColor: '#1a2940',
  },
  title: {
    color: '#fff',
    fontSize: 24,
    fontWeight: 'bold',
  },
  segmented: {
    margin: 10,
    height: 36,
  },
  cardRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    padding: 10,
  },
  card: {
    flex: 1,
    margin: 5,
    backgroundColor: '#1a2940',
  },
  chartCard: {
    margin: 10,
    backgroundColor: '#1a2940',
  },
  label: {
    color: '#888',
    fontSize: 12,
  },
  value: {
    color: '#fff',
    fontSize: 20,
    fontWeight: 'bold',
  },
  chartTitle: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  chart: {
    borderRadius: 16,
  },
  symbolRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  symbolName: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  symbolTrades: {
    color: '#888',
    fontSize: 12,
  },
  symbolPnl: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  riskRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  riskLabel: {
    color: '#888',
    fontSize: 14,
  },
  riskValue: {
    color: '#fff',
    fontSize: 14,
    fontWeight: 'bold',
  },
});

export default AnalyticsScreen;
