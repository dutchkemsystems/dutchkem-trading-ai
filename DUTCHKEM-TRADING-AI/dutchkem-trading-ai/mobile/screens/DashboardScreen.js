import React from 'react';
import { View, ScrollView, StyleSheet } from 'react-native';
import { Card, Text, ProgressBar, Surface, Avatar } from 'react-native-paper';

const DashboardScreen = () => {
  return (
    <ScrollView style={styles.container}>
      <Surface style={styles.header}>
        <Avatar.Text size={50} label="JD" style={styles.avatar} />
        <View>
          <Text style={styles.greeting}>Good Morning,</Text>
          <Text style={styles.name}>John Doe</Text>
        </View>
      </Surface>

      <View style={styles.cardRow}>
        <Card style={styles.card}>
          <Card.Content>
            <Text style={styles.cardLabel}>Balance</Text>
            <Text style={styles.cardValue}>$10,450</Text>
          </Card.Content>
        </Card>
        <Card style={styles.card}>
          <Card.Content>
            <Text style={styles.cardLabel}>Equity</Text>
            <Text style={styles.cardValue}>$10,580</Text>
          </Card.Content>
        </Card>
      </View>

      <Card style={styles.fullCard}>
        <Card.Content>
          <Text style={styles.cardLabel}>Daily P&L</Text>
          <Text style={[styles.cardValue, { color: '#4caf50' }]}>+$130 (0.12%)</Text>
          <ProgressBar progress={0.3} color="#4caf50" style={styles.progress} />
        </Card.Content>
      </Card>

      <Card style={styles.fullCard}>
        <Card.Content>
          <Text style={styles.cardLabel}>Risk Status</Text>
          <View style={styles.riskRow}>
            <Text>Daily Loss</Text>
            <Text>0.5% / 2%</Text>
          </View>
          <ProgressBar progress={0.25} color="#4caf50" style={styles.progress} />
          <View style={styles.riskRow}>
            <Text>Drawdown</Text>
            <Text>1.2% / 15%</Text>
          </View>
          <ProgressBar progress={0.08} color="#1976d2" style={styles.progress} />
        </Card.Content>
      </Card>

      <Card style={styles.fullCard}>
        <Card.Content>
          <Text style={styles.cardLabel}>Active Signals</Text>
          <View style={styles.signalItem}>
            <Text>EURUSD</Text>
            <Text style={{ color: '#4caf50' }}>LONG 85%</Text>
          </View>
          <View style={styles.signalItem}>
            <Text>GBPUSD</Text>
            <Text style={{ color: '#f44336' }}>SHORT 72%</Text>
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
    flexDirection: 'row',
    alignItems: 'center',
    padding: 20,
    backgroundColor: '#1a2940',
  },
  avatar: {
    backgroundColor: '#1976d2',
    marginRight: 15,
  },
  greeting: {
    color: '#888',
    fontSize: 14,
  },
  name: {
    color: '#fff',
    fontSize: 20,
    fontWeight: 'bold',
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
  fullCard: {
    margin: 10,
    backgroundColor: '#1a2940',
  },
  cardLabel: {
    color: '#888',
    fontSize: 12,
  },
  cardValue: {
    color: '#fff',
    fontSize: 24,
    fontWeight: 'bold',
  },
  progress: {
    marginTop: 10,
    height: 8,
    borderRadius: 4,
  },
  riskRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 10,
  },
  signalItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
});

export default DashboardScreen;
