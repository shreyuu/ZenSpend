export default function ExpenseList({ expenses }) {
    return (
        <div className="max-w-md mx-auto bg-white p-4 shadow rounded">
            <h2 className="text-xl text-stone-950 font-bold mb-4">Expenses</h2>
            {expenses.map((exp) => (
                <div key={exp.id} className="border-b text-stone-950 py-2">
                    ₹{exp.amount} • {exp.category}
                    <div className="text-sm text-stone-950">{exp.note}</div>
                </div>
            ))}
        </div>
    )
}