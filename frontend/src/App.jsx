import { useState } from 'react'
import ExpenseForm from './components/ExpenseForm'
import ExpenseList from './components/ExpenseList'

function App() {
  const [expenses, setExpenses] = useState([])

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