import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useSelector } from 'react-redux';
import Layout from './components/Layout';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Trading from './pages/Trading';
import Signals from './pages/Signals';
import RiskManagement from './pages/RiskManagement';
import Payments from './pages/Payments';
import ExpertAdvisors from './pages/ExpertAdvisors';
import Settings from './pages/Settings';
import Analytics from './pages/Analytics';

const PrivateRoute = ({ children }) => {
  const { isAuthenticated } = useSelector((state) => state.auth);
  return isAuthenticated ? children : <Navigate to="/login" />;
};

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route
          path="/"
          element={
            <PrivateRoute>
              <Layout />
            </PrivateRoute>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="trading" element={<Trading />} />
          <Route path="signals" element={<Signals />} />
          <Route path="risk" element={<RiskManagement />} />
          <Route path="payments" element={<Payments />} />
          <Route path="eas" element={<ExpertAdvisors />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
