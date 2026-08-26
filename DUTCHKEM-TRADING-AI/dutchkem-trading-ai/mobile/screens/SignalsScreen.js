import React from 'react';
import { View, ScrollView, StyleSheet } from 'react-native';
import { Card, Text, Surface, Chip } from 'react-native-paper';

const SignalsScreen = () => {
  const signals = [
    { id: 1, symbol: 'EURUSD', direction: 'LONG', score: 85, timeframe: 'H1' },
    { id: 2, symbol: 'GBPUSD', direction: 'SHORT', score: 72, timeframe: 'M15' },
    { id: 3, symbol: 'USDJPY', direction: 'LONG', score: 68, timeframe: 'H4' },
  ];

  return (
    <ScrollView style={styles.container}>
      <Surface style={styles.header}>
        <Text style={styles.title}>Signals</Text>
      </Surface>

      <View style={styles.summaryRow}>
        <Card style={styles.summaryCard}>
          <Card.Content>
            <Text style={styles.summaryLabel}>Active</Text>
            <Text style={styles.summaryValue}>3</Text>
          </Card.Content>
        </Card>
        <Card style={styles.summaryCard}>
          <Card.Content>
            <Text style={styles.summaryLabel}>Strong</Text>
            <Text style={[styles.summaryValue, { color: '#4caf50' }]}>1</Text>
          </Card.Content>
        </Card>
        <Card style={styles.summaryCard}>
          <Card.Content>
            <Text style={styles.summaryLabel}>Win Rate</Text>
            <Text style={styles.summaryValue}>62%</Text>
          </Card.Content>
        </Card>
      </View>

      {signals.map((signal) => (
        <Card key={signal.id} style={styles.signalCard}>
          <Card.Content>
            <View style={styles.signalHeader}>
              <Text style={styles.symbol}>{signal.symbol}</Text>
              <Chip
                mode="outlined"
                style={[
                  styles.directionChip,
                  { borderColor: signal.direction === 'LONG' ? '#4caf50' : '#f44336' }
                ]}
                textStyle={{ color: signal.direction === 'LONG' ? '#4caf50' : '#f44336' }}
              >
                {signal.direction}
              </Chip>
            </View>
            <View style={styles.signalDetails}>
              <View>
                <Text style={styles.label}>Score</Text>
                <Text style={styles.value}>{signal.score}%</Text>
              </View>
              <View>
                <Text style={styles.label}>Timeframe</Text>
                <Text style={styles.value}>{signal.timeframe}</Text>
              </View>
            </View>
          </Card.Content>
        </Card>
      ))}
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
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    padding: 10,
  },
  summaryCard: {
    flex: 1,
    margin: 5,
    backgroundColor: '#1a2940',
  },
  summaryLabel: {
    color: '#888',
    fontSize: 12,
  },
  summaryValue: {
    color: '#fff',
    fontSize: 20,
    fontWeight: 'bold',
  },
  signalCard: {
    margin: 10,
    backgroundColor: '#1a2940',
  },
  signalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  symbol: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
  },
  directionChip: {
    borderWidth: 1,
  },
  signalDetails: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginTop: 15,
  },
  label: {
    color: '#888',
    fontSize: 12,
  },
  value: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
});

export default SignalsScreen;
