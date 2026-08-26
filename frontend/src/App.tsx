import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Wallet from './pages/Wallet'
import Transactions from './pages/Transactions'
import Agents from './pages/Agents'
import Pillars from './pages/Pillars'
import Settings from './pages/Settings'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/wallet" element={<Wallet />} />
        <Route path="/transactions" element={<Transactions />} />
        <Route path="/agents" element={<Agents />} />
        <Route path="/pillars" element={<Pillars />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
    </Routes>
  )
}
