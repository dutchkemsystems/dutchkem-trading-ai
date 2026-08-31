import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Provider } from 'react-redux';
import { PaperProvider, DefaultTheme } from 'react-native-paper';
import { Ionicons } from '@expo/vector-icons';
import { store } from './store';
import DashboardScreen from './screens/DashboardScreen';
import TradingScreen from './screens/TradingScreen';
import SignalsScreen from './screens/SignalsScreen';
import AnalyticsScreen from './screens/AnalyticsScreen';
import ProfileScreen from './screens/ProfileScreen';

const Tab = createBottomTabNavigator();

const theme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    primary: '#1976d2',
    accent: '#dc004e',
    background: '#0a1929',
    surface: '#1a2940',
    text: '#ffffff',
  },
};

export default function App() {
  return (
    <Provider store={store}>
      <PaperProvider theme={theme}>
        <NavigationContainer>
          <Tab.Navigator
            screenOptions={({ route }) => ({
              tabBarIcon: ({ focused, color, size }) => {
                let iconName;
                if (route.name === 'Dashboard') iconName = focused ? 'home' : 'home-outline';
                else if (route.name === 'Trading') iconName = focused ? 'trending-up' : 'trending-up-outline';
                else if (route.name === 'Signals') iconName = focused ? 'speedometer' : 'speedometer-outline';
                else if (route.name === 'Analytics') iconName = focused ? 'stats-chart' : 'stats-chart-outline';
                else if (route.name === 'Profile') iconName = focused ? 'person' : 'person-outline';
                return <Ionicons name={iconName} size={size} color={color} />;
              },
              tabBarActiveTintColor: '#1976d2',
              tabBarInactiveTintColor: 'gray',
              headerStyle: { backgroundColor: '#1a2940' },
              headerTintColor: '#fff',
            })}
          >
            <Tab.Screen name="Dashboard" component={DashboardScreen} />
            <Tab.Screen name="Trading" component={TradingScreen} />
            <Tab.Screen name="Signals" component={SignalsScreen} />
            <Tab.Screen name="Analytics" component={AnalyticsScreen} />
            <Tab.Screen name="Profile" component={ProfileScreen} />
          </Tab.Navigator>
        </NavigationContainer>
        <StatusBar style="light" />
      </PaperProvider>
    </Provider>
  );
}
