import React, { useEffect, useState } from 'react';
import { View, ScrollView, StyleSheet, ActivityIndicator } from 'react-native';
import { Card, Text, Button, Surface } from 'react-native-paper';
import { useDispatch, useSelector } from 'react-redux';
import { fetchPositions } from '../store';
import { tradingAPI } from '../services/api';

const TradingScreen = () => {
  const dispatch = useDispatch();
  const { positions, loading } = useSelector((s) => s.trading);
  const [timeframe, setTimeframe] = useState('H1');

  useEffect(() => { dispatch(fetchPositions()); }, [dispatch]);

  const handleTrade = async (direction) => {
    try {
      await tradingAPI.createOrder({
        symbol: 'EURUSD',
        order_type: 'MARKET',
        position_type: direction,
        volume: 0.1,
      });
      dispatch(fetchPositions());
    } catch (err) {
      console.error('Order failed:', err);
    }
  };

  return (
    <ScrollView style={styles.container}>
      <Surface style={styles.header}>
        <Text style={styles.title}>Trading</Text>
      </Surface>

      <View style={styles.timeframeContainer}>
        {['M5', 'M15', 'M30', 'H1', 'H2', 'H4'].map((tf) => (
          <Button key={tf} mode={timeframe === tf ? 'contained' : 'outlined'}
            onPress={() => setTimeframe(tf)} style={styles.timeframeButton} compact>
            {tf}
          </Button>
        ))}
      </View>

      {loading ? (
        <ActivityIndicator size="large" color="#1976d2" style={{ marginTop: 40 }} />
      ) : (
        <Card style={styles.card}>
          <Card.Content>
            <Text style={styles.cardTitle}>Open Positions ({positions.length})</Text>
            {positions.length === 0 ? (
              <Text style={styles.emptyText}>No open positions</Text>
            ) : positions.map((pos, idx) => (
              <View key={pos.id || idx} style={styles.positionRow}>
                <View>
                  <Text style={styles.symbol}>{pos.symbol?.name || pos.symbol}</Text>
                  <Text style={styles.type}>{pos.position_type} {pos.volume}</Text>
                </View>
                <Text style={[styles.pnl, { color: parseFloat(pos.unrealized_pnl) >= 0 ? '#4caf50' : '#f44336' }]}>
                  ${Number(pos.unrealized_pnl).toFixed(2)}
                </Text>
              </View>
            ))}
          </Card.Content>
        </Card>
      )}

      <View style={styles.buttonRow}>
        <Button mode="contained" style={[styles.tradeButton, { backgroundColor: '#4caf50' }]}
          onPress={() => handleTrade('BUY')}>
          BUY
        </Button>
        <Button mode="contained" style={[styles.tradeButton, { backgroundColor: '#f44336' }]}
          onPress={() => handleTrade('SELL')}>
          SELL
        </Button>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0a1929' },
  header: { padding: 20, backgroundColor: '#1a2940' },
  title: { color: '#fff', fontSize: 24, fontWeight: 'bold' },
  timeframeContainer: { flexDirection: 'row', justifyContent: 'space-around', padding: 10 },
  timeframeButton: { minWidth: 50 },
  card: { margin: 10, backgroundColor: '#1a2940' },
  cardTitle: { color: '#fff', fontSize: 16, fontWeight: 'bold', marginBottom: 10 },
  positionRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#333' },
  symbol: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
  type: { color: '#888', fontSize: 12 },
  pnl: { fontSize: 16, fontWeight: 'bold' },
  buttonRow: { flexDirection: 'row', justifyContent: 'space-around', padding: 20 },
  tradeButton: { flex: 1, marginHorizontal: 10 },
  emptyText: { color: '#888', textAlign: 'center', padding: 20 },
});

export default TradingScreen;
