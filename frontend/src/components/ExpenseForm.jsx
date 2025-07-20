import { useState } from 'react'

export default function ExpenseForm({ onAdd }) {
    const [amount, setAmount] = useState('')
    const [category, setCategory] = useState('')
    const [note, setNote] = useState('')

    const handleSubmit = async (e) => {
        e.preventDefault()
        const data = { amount: parseFloat(amount), category, note }

        const res = await fetch('http://localhost:8000/add-expense', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        })
        const json = await res.json()
        onAdd(json)
        setAmount('')
        setCategory('')
        setNote('')
    }

    return (
        <form onSubmit={handleSubmit} className="p-4 space-y-4 bg-white rounded shadow max-w-md mx-auto my-6">
            <input className="w-full text-black border p-2 rounded" type="number" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="Amount" required />
            <input className="w-full text-black border p-2 rounded" value={category} onChange={(e) => setCategory(e.target.value)} placeholder="Category" required />
            <input className="w-full text-black border p-2 rounded" value={note} onChange={(e) => setNote(e.target.value)} placeholder="Note (optional)" />
            <button className="w-full bg-blue-500 text-white p-2 rounded hover:bg-blue-600">Add Expense</button>
        </form>
    )
}