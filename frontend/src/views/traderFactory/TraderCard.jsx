import React, { useState } from "react";
import "./TraderCard.css";

export default function TraderCard({ trader, onDelete }) {
  const [flipped, setFlipped] = useState(false);
  const avatar = trader.avatar || "🤖";
  const heat = trader.heat_index?.toFixed?.(1);

  return (
    <div className={\`flip-card \${flipped ? "flipped" : ""}\`}
         onClick={() => setFlipped(!flipped)}>
      <div className="flip-card-inner">
        {/* FRONT */}
        <div className="flip-card-front">
          <span className="avatar">{avatar}</span>
          <h4>{trader.name}</h4>
          <p>${'{'}trader.wallet_balance?.toLocaleString(){'}'}</p>
        </div>

        {/* BACK */}
        <div className="flip-card-back">
          <p>Profit: ${'{'}trader.profit{'}'}</p>
          <p>Heat: {heat}</p>
          <p>Mood: {trader.mood}</p>
          <p>Strategies: {Object.keys(trader.strategies || {}).length}</p>
          <button onClick={e => {e.stopPropagation(); onDelete(trader.name);}}>
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}
