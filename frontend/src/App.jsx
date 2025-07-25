import { useState, useEffect } from 'react'
import ExpenseForm from './components/ExpenseForm'
import ExpenseList from './components/ExpenseList'

function App() {
  const [expenses, setExpenses] = useState([])

  // Fetch expenses on component mount
  useEffect(() => {
    const fetchExpenses = async () => {
      try {
        const res = await fetch('http://localhost:8000/expenses')
        const data = await res.json()
        setExpenses(data)
      } catch (error) {
        console.error('Failed to fetch expenses:', error)
      }
    }

    fetchExpenses()
  }, [])

  const handleAdd = (newExpense) => {
    setExpenses([newExpense, ...expenses])
  }

  return (
    <div className="min-h-screen w-screen bg-gray-100 p-4">
      <h1 className="text-3xl text-stone-950 font-bold text-center mb-4">💸 ZenSpend</h1>
      <ExpenseForm onAdd={handleAdd} />
      <ExpenseList expenses={expenses} />
    </div>
  )
}

export default App