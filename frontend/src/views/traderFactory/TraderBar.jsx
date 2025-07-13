import React, { useEffect, useState } from "react";
import TraderCard from "./TraderCard";

export default function TraderBar() {
  const [traders, setTraders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState("");

  const load = async () => {
    setLoading(true);
    const res = await fetch("/api/traders");
    const data = await res.json();
    setTraders(Array.isArray(data) ? data : []);
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  const createTrader = async () => {
    if (!newName) return;
    await fetch("/api/traders/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: newName })
    });
    setNewName("");
    load();
  };

  const deleteTrader = async (name) => {
    await fetch(\`/api/traders/\${encodeURIComponent(name)}/delete\`, { method:"POST" });
    load();
  };

  if (loading) return <p>Loading…</p>;

  return (
    <>
      <div style={{marginBottom:"1rem"}}>
        <input value={newName} placeholder="Trader name"
               onChange={e=>setNewName(e.target.value)} />
        <button onClick={createTrader}>Create</button>
      </div>
      <div style={{display:"flex", overflowX:"auto"}}>
        {traders.map(t => (
          <TraderCard key={t.name} trader={t} onDelete={deleteTrader} />
        ))}
      </div>
    </>
  );
}
