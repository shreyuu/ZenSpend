export default function ExpenseList({ expenses }) {
    return (
        <div className="max-w-md mx-auto bg-white p-4 shadow rounded">
            <h2 className="text-xl font-bold mb-4">Expenses</h2>
            {expenses.map((exp) => (
                <div key={exp.id} className="border-b py-2">
                    ₹{exp.amount} • {exp.category}
                    <div className="text-sm text-gray-500">{exp.note}</div>
                </div>
            ))}
        </div>
    )
}