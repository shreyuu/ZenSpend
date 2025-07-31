import { useState } from "react";
import axios from "axios";

export default function ChatBox() {
    const [messages, setMessages] = useState([]);
    const [userMsg, setUserMsg] = useState("");

    const handleSend = async () => {
        if (!userMsg.trim()) return;

        const newMsg = { role: "user", content: userMsg };
        setMessages((prev) => [...prev, newMsg]);
        setUserMsg("");

        try {
            const res = await axios.post("http://localhost:8000/ask", {
                message: userMsg,
            });
            const aiReply = res.data.response;

            setMessages((prev) => [
                ...prev,
                { role: "assistant", content: aiReply },
            ]);
        } catch (err) {
            console.error("Error:", err);
        }
    };

    return (
        <div className="flex flex-col h-screen p-4 bg-gray-100">
            <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-white rounded shadow">
                {messages.map((msg, idx) => (
                    <div
                        key={idx}
                        className={`p-2 rounded-lg max-w-md ${msg.role === "user"
                                ? "bg-blue-100 self-end text-right"
                                : "bg-gray-200 self-start"
                            }`}
                    >
                        {msg.content}
                    </div>
                ))}
            </div>
            <div className="mt-4 flex gap-2">
                <input
                    value={userMsg}
                    onChange={(e) => setUserMsg(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSend()}
                    className="flex-1 p-2 rounded border border-gray-400"
                    placeholder="Ask your expense assistant..."
                />
                <button
                    onClick={handleSend}
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                    Send
                </button>
            </div>
        </div>
    );
}