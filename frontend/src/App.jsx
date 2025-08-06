import { useState, useEffect } from "react";
import ChatBox from "./components/ChatBot";
import ExpenseForm from "./components/ExpenseForm";
import ExpenseList from "./components/ExpenseList";

function App() {
  const [expenses, setExpenses] = useState([]);

  useEffect(() => {
    // Fetch expenses when component mounts
    fetchExpenses();
  }, []);

  const fetchExpenses = async () => {
    try {
      const response = await fetch("http://localhost:8000/expenses");
      const data = await response.json();
      setExpenses(data);
    } catch (error) {
      console.error("Error fetching expenses:", error);
    }
  };

  const handleAddExpense = (newExpense) => {
    setExpenses([newExpense, ...expenses]);
  };

  return (
    <div className="min-h-screen w-screen bg-gray-100 p-4">
      <h1 className="text-3xl text-stone-950 font-bold text-center mb-4">💸 ZenSpend</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="flex flex-col gap-6">
          <ExpenseForm onAdd={handleAddExpense} />
          <ExpenseList expenses={expenses} />
        </div>

        <div>
          <ChatBox />
        </div>
      </div>
    </div>
  );
}

export default App;
