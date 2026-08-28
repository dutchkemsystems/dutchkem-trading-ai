import React, { useEffect, useState } from 'react';
import { View, ScrollView, StyleSheet } from 'react-native';
import { Card, Text, Surface, Avatar, List, Divider } from 'react-native-paper';
import { useDispatch, useSelector } from 'react-redux';
import { fetchProfile, logoutUser } from '../store';

const ProfileScreen = ({ navigation }) => {
  const dispatch = useDispatch();
  const { user } = useSelector((s) => s.auth);

  useEffect(() => { dispatch(fetchProfile()); }, [dispatch]);

  const handleLogout = () => {
    dispatch(logoutUser());
  };

  const initials = ((user?.first_name?.[0] || '') + (user?.last_name?.[0] || '')).toUpperCase() || 'U';

  return (
    <ScrollView style={styles.container}>
      <Surface style={styles.header}>
        <Avatar.Text size={80} label={initials} style={styles.avatar} />
        <Text style={styles.name}>{user?.first_name} {user?.last_name}</Text>
        <Text style={styles.email}>{user?.email}</Text>
      </Surface>

      <Card style={styles.card}>
        <Card.Content>
          <Text style={styles.cardTitle}>Account Summary</Text>
          <View style={styles.summaryRow}>
            <View style={styles.summaryItem}>
              <Text style={styles.summaryLabel}>Balance</Text>
              <Text style={styles.summaryValue}>${Number(user?.balance || 0).toLocaleString()}</Text>
            </View>
            <View style={styles.summaryItem}>
              <Text style={styles.summaryLabel}>Equity</Text>
              <Text style={styles.summaryValue}>${Number(user?.equity || 0).toLocaleString()}</Text>
            </View>
            <View style={styles.summaryItem}>
              <Text style={styles.summaryLabel}>KYC</Text>
              <Text style={[styles.summaryValue, { color: user?.kyc_status === 'VERIFIED' ? '#4caf50' : '#f44336' }]}>
                {user?.kyc_status || 'NOT_STARTED'}
              </Text>
            </View>
          </View>
        </Card.Content>
      </Card>

      <Card style={styles.card}>
        <List.Item title="MT5 Connection"
          description={user?.mt5_account ? `${user.mt5_server} (${user.mt5_account})` : 'Not connected'}
          left={(props) => <List.Icon {...props} icon="link" />}
          right={(props) => <List.Icon {...props} icon="chevron-right" />} />
        <Divider />
        <List.Item title="Security"
          description={user?.mfa_enabled ? 'MFA Enabled' : 'MFA Disabled'}
          left={(props) => <List.Icon {...props} icon="shield" />}
          right={(props) => <List.Icon {...props} icon="chevron-right" />} />
        <Divider />
        <List.Item title="Notifications"
          left={(props) => <List.Icon {...props} icon="bell" />}
          right={(props) => <List.Icon {...props} icon="chevron-right" />} />
      </Card>

      <Card style={styles.card}>
        <List.Item title="Logout" onPress={handleLogout}
          left={(props) => <List.Icon {...props} icon="logout" color="#f44336" />}
          titleStyle={{ color: '#f44336' }} />
      </Card>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0a1929' },
  header: { alignItems: 'center', padding: 30, backgroundColor: '#1a2940' },
  avatar: { backgroundColor: '#1976d2', marginBottom: 15 },
  name: { color: '#fff', fontSize: 24, fontWeight: 'bold' },
  email: { color: '#888', fontSize: 14 },
  card: { margin: 10, backgroundColor: '#1a2940' },
  cardTitle: { color: '#fff', fontSize: 16, fontWeight: 'bold', marginBottom: 15 },
  summaryRow: { flexDirection: 'row', justifyContent: 'space-between' },
  summaryItem: { alignItems: 'center' },
  summaryLabel: { color: '#888', fontSize: 12 },
  summaryValue: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
});

export default ProfileScreen;
