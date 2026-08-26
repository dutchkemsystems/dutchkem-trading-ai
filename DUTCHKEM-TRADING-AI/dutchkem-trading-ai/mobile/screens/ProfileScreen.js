import React from 'react';
import { View, ScrollView, StyleSheet } from 'react-native';
import { Card, Text, Surface, Avatar, List, Divider } from 'react-native-paper';
import { Ionicons } from '@expo/vector-icons';

const ProfileScreen = () => {
  return (
    <ScrollView style={styles.container}>
      <Surface style={styles.header}>
        <Avatar.Text size={80} label="JD" style={styles.avatar} />
        <Text style={styles.name}>John Doe</Text>
        <Text style={styles.email}>john@example.com</Text>
      </Surface>

      <Card style={styles.card}>
        <Card.Content>
          <Text style={styles.cardTitle}>Account Summary</Text>
          <View style={styles.summaryRow}>
            <View style={styles.summaryItem}>
              <Text style={styles.summaryLabel}>Balance</Text>
              <Text style={styles.summaryValue}>$10,450</Text>
            </View>
            <View style={styles.summaryItem}>
              <Text style={styles.summaryLabel}>Equity</Text>
              <Text style={styles.summaryValue}>$10,580</Text>
            </View>
            <View style={styles.summaryItem}>
              <Text style={styles.summaryLabel}>Daily P&L</Text>
              <Text style={[styles.summaryValue, { color: '#4caf50' }]}>+0.12%</Text>
            </View>
          </View>
        </Card.Content>
      </Card>

      <Card style={styles.card}>
        <List.Item
          title="Settings"
          left={(props) => <List.Icon {...props} icon="cog" />}
          right={(props) => <List.Icon {...props} icon="chevron-right" />}
        />
        <Divider />
        <List.Item
          title="Security"
          left={(props) => <List.Icon {...props} icon="shield" />}
          right={(props) => <List.Icon {...props} icon="chevron-right" />}
        />
        <Divider />
        <List.Item
          title="Notifications"
          left={(props) => <List.Icon {...props} icon="bell" />}
          right={(props) => <List.Icon {...props} icon="chevron-right" />}
        />
        <Divider />
        <List.Item
          title="MT5 Connection"
          left={(props) => <List.Icon {...props} icon="link" />}
          right={(props) => <List.Icon {...props} icon="chevron-right" />}
        />
        <Divider />
        <List.Item
          title="Payment Methods"
          left={(props) => <List.Icon {...props} icon="credit-card" />}
          right={(props) => <List.Icon {...props} icon="chevron-right" />}
        />
      </Card>

      <Card style={styles.card}>
        <List.Item
          title="Logout"
          left={(props) => <List.Icon {...props} icon="logout" color="#f44336" />}
          titleStyle={{ color: '#f44336' }}
        />
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
    alignItems: 'center',
    padding: 30,
    backgroundColor: '#1a2940',
  },
  avatar: {
    backgroundColor: '#1976d2',
    marginBottom: 15,
  },
  name: {
    color: '#fff',
    fontSize: 24,
    fontWeight: 'bold',
  },
  email: {
    color: '#888',
    fontSize: 14,
  },
  card: {
    margin: 10,
    backgroundColor: '#1a2940',
  },
  cardTitle: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 15,
  },
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  summaryItem: {
    alignItems: 'center',
  },
  summaryLabel: {
    color: '#888',
    fontSize: 12,
  },
  summaryValue: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
});

export default ProfileScreen;
