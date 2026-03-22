import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Orders from './pages/Orders'
import Reconciliation from './pages/Reconciliation'
import Tax from './pages/Tax'
import Profit from './pages/Profit'
import AIAnalysis from './pages/AIAnalysis'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/orders" element={<Orders />} />
        <Route path="/reconciliation" element={<Reconciliation />} />
        <Route path="/tax" element={<Tax />} />
        <Route path="/profit" element={<Profit />} />
        <Route path="/ai" element={<AIAnalysis />} />
      </Route>
    </Routes>
  )
}
