import { useState, useEffect, useRef } from "react";
import axios from "axios";

export default function ChatBox() {
    const [messages, setMessages] = useState([]);
    const [userMsg, setUserMsg] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef(null);

    // Auto-scroll to bottom when messages change
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const handleSend = async () => {
        if (!userMsg.trim()) return;

        const newMsg = { role: "user", content: userMsg };
        setMessages((prev) => [...prev, newMsg]);
        setUserMsg("");
        setIsLoading(true);

        // Check if this is an expense pattern
        const isExpensePattern = /(?:spent|paid|bought|expense|rupees|₹|rs\.?)\s+(\d+)/i.test(userMsg);

        try {
            let aiReply;

            // If it looks like an expense, try the direct expense endpoint first
            if (isExpensePattern) {
                try {
                    const directResult = await addExpenseDirectly(userMsg);
                    if (directResult) {
                        setMessages((prev) => [
                            ...prev,
                            { role: "assistant", content: directResult }
                        ]);
                        setIsLoading(false);
                        return;
                    }
                } catch (error) {
                    // Log the error to properly use the variable
                    console.log("Direct expense addition failed, falling back to agent:", error);
                    // Fall through to regular agent if direct method fails
                }
            }

            // Use the regular agent as fallback
            const res = await axios.post("http://localhost:8000/ask", {
                message: userMsg,
            });
            aiReply = res.data.response;

            // Handle error responses gracefully
            if (aiReply.includes("Agent stopped due to iteration limit") ||
                aiReply.includes("error") ||
                aiReply.includes("I'm sorry")) {

                // If it was an expense pattern that failed, try to extract it ourselves
                if (isExpensePattern) {
                    const expenseMatch = userMsg.match(/(\d+)(?:\s+(?:rupees|₹|rs\.?))?(?:\s+(?:for|on)\s+)?(.*?)(?:\s+on\s+(.*))?$/i);

                    if (expenseMatch) {
                        const amount = expenseMatch[1];
                        const categoryText = expenseMatch[2] || "Miscellaneous";
                        // Store the date text but use it in the API call below
                        const parsedDate = expenseMatch[3] || "today";

                        aiReply = `I've added your expense of ₹${amount} for ${categoryText}. Would you like to add more details or categorize it differently?`;

                        // Optionally make a real API call here to save the expense
                        try {
                            await axios.post("http://localhost:8000/add-expense", {
                                amount: parseFloat(amount),
                                category: categoryText.trim().charAt(0).toUpperCase() + categoryText.trim().slice(1),
                                note: userMsg,
                                // Use the parsed date if we need it in the API call
                                date: parsedDate === "today" ? new Date().toISOString().split('T')[0] : parsedDate
                            });
                        } catch (error) {
                            console.error("Error saving extracted expense:", error);
                        }
                    } else {
                        aiReply = "I'm having trouble understanding that expense. Could you try a format like 'Spent ₹500 on groceries'?";
                    }
                } else {
                    aiReply = "I'm not sure how to help with that. Could you try rephrasing or ask me about your expenses?";
                }
            }

            setMessages((prev) => [
                ...prev,
                { role: "assistant", content: aiReply },
            ]);
        } catch (error) {
            console.error("Error:", error);
            setMessages((prev) => [
                ...prev,
                { role: "assistant", content: "Sorry, I encountered an error. Please try again." },
            ]);
        } finally {
            setIsLoading(false);
        }
    };

    // Direct expense addition method
    const addExpenseDirectly = async (expenseText) => {
        try {
            const res = await axios.post("http://localhost:8000/chat-expense", {
                text: expenseText,
            });

            if (!res.data || !res.data.amount) {
                return null;
            }

            const { amount, category, date, description } = res.data;

            // Format date nicely
            const formattedDate = new Date(date).toLocaleDateString(undefined, {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });

            return `✅ Added expense: ₹${amount} for ${category || 'Miscellaneous'} on ${formattedDate}${description ? ` (${description})` : ''}`;
        } catch (error) {
            console.error("Direct expense addition error:", error);
            return null;
        }
    };

    return (
        <div className="flex flex-col h-screen p-4 bg-gray-100 rounded-lg shadow-md">
            <h2 className="text-xl font-semibold text-stone-950 mb-4">Expense Assistant</h2>

            <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-white rounded shadow">
                {messages.length === 0 && (
                    <div className="text-gray-500 text-center py-4">
                        <p>👋 Hi! I'm your ZenSpend assistant.</p>
                        <p className="text-sm mt-2">Try saying something like:</p>
                        <ul className="text-sm mt-1 text-blue-600">
                            <li>"I spent ₹342 for table on 28 July 2025"</li>
                            <li>"Add ₹1200 for shopping"</li>
                            <li>"How much did I spend this month?"</li>
                        </ul>
                    </div>
                )}

                {messages.map((msg, idx) => (
                    <div
                        key={idx}
                        className={`p-3 rounded-lg max-w-md ${msg.role === "user"
                            ? "bg-blue-100 ml-auto text-right"
                            : "bg-gray-200 mr-auto"
                            }`}
                    >
                        {msg.content}
                    </div>
                ))}

                {isLoading && (
                    <div className="bg-gray-200 p-3 rounded-lg max-w-md flex items-center space-x-2">
                        <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: "0.2s" }}></div>
                        <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: "0.4s" }}></div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            <div className="mt-4 flex gap-2">
                <input
                    value={userMsg}
                    onChange={(e) => setUserMsg(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
                    className="flex-1 p-2 rounded border border-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Ask your expense assistant..."
                    disabled={isLoading}
                />
                <button
                    onClick={handleSend}
                    className={`px-4 py-2 text-white rounded ${isLoading || !userMsg.trim()
                        ? "bg-blue-400 cursor-not-allowed"
                        : "bg-blue-600 hover:bg-blue-700"
                        }`}
                    disabled={isLoading || !userMsg.trim()}
                >
                    {isLoading ? "Sending..." : "Send"}
                </button>
            </div>
        </div>
    );
}