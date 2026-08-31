import React, { useEffect } from 'react';
import { View, ScrollView, StyleSheet, ActivityIndicator } from 'react-native';
import { Card, Text, Surface, Chip } from 'react-native-paper';
import { useDispatch, useSelector } from 'react-redux';
import { fetchActiveSignals } from '../store';

const SignalsScreen = () => {
  const dispatch = useDispatch();
  const { activeSignals, loading } = useSelector((s) => s.signals);

  useEffect(() => { dispatch(fetchActiveSignals()); }, [dispatch]);

  const strong = activeSignals.filter((s) => (s.strength || 0) >= 80);

  return (
    <ScrollView style={styles.container}>
      <Surface style={styles.header}>
        <Text style={styles.title}>Signals</Text>
      </Surface>

      <View style={styles.summaryRow}>
        <Card style={styles.summaryCard}>
          <Card.Content>
            <Text style={styles.summaryLabel}>Active</Text>
            <Text style={styles.summaryValue}>{activeSignals.length}</Text>
          </Card.Content>
        </Card>
        <Card style={styles.summaryCard}>
          <Card.Content>
            <Text style={styles.summaryLabel}>Strong</Text>
            <Text style={[styles.summaryValue, { color: '#4caf50' }]}>{strong.length}</Text>
          </Card.Content>
        </Card>
      </View>

      {loading ? (
        <ActivityIndicator size="large" color="#1976d2" style={{ marginTop: 40 }} />
      ) : activeSignals.length === 0 ? (
        <Text style={styles.emptyText}>No active signals</Text>
      ) : activeSignals.map((signal, idx) => (
        <Card key={signal.id || idx} style={styles.signalCard}>
          <Card.Content>
            <View style={styles.signalHeader}>
              <Text style={styles.symbol}>{signal.symbol?.name || signal.symbol}</Text>
              <Chip mode="outlined"
                style={[styles.directionChip, { borderColor: signal.signal_type === 'BUY' ? '#4caf50' : '#f44336' }]}
                textStyle={{ color: signal.signal_type === 'BUY' ? '#4caf50' : '#f44336' }}>
                {signal.signal_type}
              </Chip>
            </View>
            <View style={styles.signalDetails}>
              <View>
                <Text style={styles.label}>Score</Text>
                <Text style={styles.value}>{signal.strength || 0}%</Text>
              </View>
              <View>
                <Text style={styles.label}>Timeframe</Text>
                <Text style={styles.value}>{signal.timeframe?.code || signal.timeframe}</Text>
              </View>
            </View>
          </Card.Content>
        </Card>
      ))}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0a1929' },
  header: { padding: 20, backgroundColor: '#1a2940' },
  title: { color: '#fff', fontSize: 24, fontWeight: 'bold' },
  summaryRow: { flexDirection: 'row', justifyContent: 'space-between', padding: 10 },
  summaryCard: { flex: 1, margin: 5, backgroundColor: '#1a2940' },
  summaryLabel: { color: '#888', fontSize: 12 },
  summaryValue: { color: '#fff', fontSize: 20, fontWeight: 'bold' },
  signalCard: { margin: 10, backgroundColor: '#1a2940' },
  signalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  symbol: { color: '#fff', fontSize: 18, fontWeight: 'bold' },
  directionChip: { borderWidth: 1 },
  signalDetails: { flexDirection: 'row', justifyContent: 'space-around', marginTop: 15 },
  label: { color: '#888', fontSize: 12 },
  value: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
  emptyText: { color: '#888', textAlign: 'center', padding: 40, fontSize: 16 },
});

export default SignalsScreen;
