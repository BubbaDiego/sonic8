import React, { useEffect, useState } from "react";
import TraderCard from "./TraderCard";
import axios from 'utils/axios';

export default function TraderBar() {
  const [traders, setTraders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const res = await axios.get("/api/traders");
      setTraders(Array.isArray(res.data) ? res.data : []);
    } catch (error) {
      console.error("Failed to load traders:", error);
    }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const createTrader = async () => {
    if (!newName) return;
    try {
      await axios.post("/api/traders", { name: newName });
      setNewName("");
      load();
    } catch (error) {
      console.error("Failed to create trader:", error);
    }
  };

  const deleteTrader = async (name) => {
    try {
      await axios.delete(`/api/traders/${encodeURIComponent(name)}`);
      load();
    } catch (error) {
      console.error("Failed to delete trader:", error);
    }
  };

  if (loading) return <p>Loading…</p>;

  return (
    <>
      <div style={{ marginBottom: "1rem" }}>
        <input
          value={newName}
          placeholder="Trader name"
          onChange={e => setNewName(e.target.value)}
        />
        <button onClick={createTrader}>Create</button>
      </div>
      <div style={{ display: "flex", overflowX: "auto" }}>
        {traders.map(t => (
          <TraderCard key={t.name} trader={t} onDelete={deleteTrader} />
        ))}
      </div>
    </>
  );
}
