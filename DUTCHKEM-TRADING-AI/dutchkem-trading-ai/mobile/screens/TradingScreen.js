import React, { useState } from 'react';
import { View, ScrollView, StyleSheet } from 'react-native';
import { Card, Text, Button, SegmentedControl, Surface } from 'react-native-paper';

const TradingScreen = () => {
  const [timeframe, setTimeframe] = useState('H1');

  const positions = [
    { id: 1, symbol: 'EURUSD', type: 'BUY', volume: 0.1, pnl: 35.00 },
    { id: 2, symbol: 'GBPUSD', type: 'SELL', volume: 0.05, pnl: 25.00 },
  ];

  return (
    <ScrollView style={styles.container}>
      <Surface style={styles.header}>
        <Text style={styles.title}>Trading</Text>
      </Surface>

      <View style={styles.timeframeContainer}>
        {['M5', 'M15', 'M30', 'H1', 'H2', 'H4'].map((tf) => (
          <Button
            key={tf}
            mode={timeframe === tf ? 'contained' : 'outlined'}
            onPress={() => setTimeframe(tf)}
            style={styles.timeframeButton}
            compact
          >
            {tf}
          </Button>
        ))}
      </View>

      <Card style={styles.card}>
        <Card.Content>
          <Text style={styles.cardTitle}>Open Positions ({positions.length})</Text>
          {positions.map((pos) => (
            <View key={pos.id} style={styles.positionRow}>
              <View>
                <Text style={styles.symbol}>{pos.symbol}</Text>
                <Text style={styles.type}>{pos.type} {pos.volume}</Text>
              </View>
              <Text style={[styles.pnl, { color: pos.pnl >= 0 ? '#4caf50' : '#f44336' }]}>
                ${pos.pnl.toFixed(2)}
              </Text>
            </View>
          ))}
        </Card.Content>
      </Card>

      <View style={styles.buttonRow}>
        <Button mode="contained" style={[styles.tradeButton, { backgroundColor: '#4caf50' }]}>
          BUY
        </Button>
        <Button mode="contained" style={[styles.tradeButton, { backgroundColor: '#f44336' }]}>
          SELL
        </Button>
      </View>
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
  timeframeContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    padding: 10,
  },
  timeframeButton: {
    minWidth: 50,
  },
  card: {
    margin: 10,
    backgroundColor: '#1a2940',
  },
  cardTitle: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  positionRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  symbol: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  type: {
    color: '#888',
    fontSize: 12,
  },
  pnl: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  buttonRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    padding: 20,
  },
  tradeButton: {
    flex: 1,
    marginHorizontal: 10,
  },
});

export default TradingScreen;
