import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { useGetActiveSession } from 'api/session';
import {
  PencilSquareIcon,
  ArrowPathIcon,
  CalendarIcon,
  ClockIcon,
  CurrencyDollarIcon
} from '@heroicons/react/24/outline';

/* ────────────────────────────────────────────────────────────────────────── */
/*                          ✨  TWEAK‑ME CONFIGS  ✨                          */
/*                                                                           */
/* 1️⃣ CARD_MAX_HEIGHT controls the absolute height of the entire flip card.  */
/*    • Unit: pixels                                                         */
/*    • If you need a taller or shorter widget, bump this number up/down.    */
export const CARD_MAX_HEIGHT = 250; // ← default: 450 px

/* ────────────────────────────────────────────────────────────────────────── */

/* Helper to robustly pull the **current total** regardless of field name */
const pickTotal = (snap) =>
  snap?.current_total_value ??
  snap?.current_total ??
  snap?.current_session_value ?? // legacy field
  snap?.current_value ??
  0;

/* Fallback snapshot for Storybook / offline demos */
const cannedSnapshot = {
  session_start_time: new Date('2025-07-13T13:39:41'),
  current_total_value: 164.41,
  session_performance_value: 0,
  session_start_value: 100,
  session_goal_value: 200
};

export default function PortfolioSessionCard({
  snapshot: snapshotProp,
  onEditStart,
  onReset
}) {
  /* --------------------------------------------------------------------- */
  /* Live data                                                             */
  /* --------------------------------------------------------------------- */
  const { session } = useGetActiveSession();
  const snapshot = snapshotProp || session || cannedSnapshot;

  /* --------------------------------------------------------------------- */
  /* Local UI state                                                        */
  /* --------------------------------------------------------------------- */
  const [flipped, setFlipped] = useState(false);
  const [editableSnapshot, setEditableSnapshot] = useState({ ...snapshot });

  useEffect(() => {
    setEditableSnapshot({ ...snapshot });
  }, [snapshot]);

  const flipCard = () => setFlipped(!flipped);

  const handleEditClick = () => {
    onEditStart?.(snapshot);
    flipCard();
  };

  const number = (n) =>
    n?.toLocaleString(undefined, {
      maximumFractionDigits: 2
    });

  /* --------------------------------------------------------------------- */
  /* Derived metrics                                                       */
  /* --------------------------------------------------------------------- */
  const currentTotal = pickTotal(snapshot);

  const perfValue =
    snapshot.session_performance_value
      ? snapshot.session_performance_value
      : currentTotal - snapshot.session_start_value;

  const perfPct = snapshot.session_start_value
    ? (perfValue / snapshot.session_start_value) * 100
    : 0;

  const progress = snapshot.session_goal_value
    ? Math.min(100, (currentTotal / snapshot.session_goal_value) * 100)
    : 0;

  /* --------------------------------------------------------------------- */
  /* Edit‑mode handlers                                                    */
  /* --------------------------------------------------------------------- */
  const handleInputChange = (field, value) => {
    setEditableSnapshot((prev) => {
      const updated = { ...prev };
      if (field === 'session_start_date') {
        const [y, m, d] = value.split('-');
        const t = new Date(updated.session_start_time);
        t.setFullYear(y, m - 1, d);
        updated.session_start_time = t;
      } else if (field === 'session_start_time') {
        const [h, min] = value.split(':');
        const t = new Date(updated.session_start_time);
        t.setHours(h, min);
        updated.session_start_time = t;
      } else {
        updated[field] = parseFloat(value);
      }
      return updated;
    });
  };

  const handleSave = () => {
    onEditStart?.(editableSnapshot);
    flipCard();
  };

  const sessionDate = snapshot.session_start_time
    ? new Date(snapshot.session_start_time)
    : new Date();

  /* --------------------------------------------------------------------- */
  /* Render                                                                */
  /* --------------------------------------------------------------------- */
  return (
    <div
      className="w-full"
      style={{ perspective: '1000px', height: CARD_MAX_HEIGHT }}
    >
      <div
        className="w-full h-full relative"
        style={{
          transition: 'transform 0.8s',
          transformStyle: 'preserve-3d',
          transform: flipped ? 'rotateY(180deg)' : 'rotateY(0deg)'
        }}
      >
        {/* FRONT SIDE ----------------------------------------------------- */}
        <div
          className="absolute w-full h-full backface-hidden flex flex-col items-center justify-start p-2"
          style={{ backfaceVisibility: 'hidden' }}
        >
          <div className="w-full bg-white shadow rounded p-2 mb-2">
            <div className="flex justify-between items-start mb-1">
              <span className="font-medium text-sm">{number(currentTotal)} USD</span>
              <button
                type="button"
                data-testid="edit-btn"
                onClick={handleEditClick}
                className="text-blue-600 hover:text-blue-800"
              >
                <PencilSquareIcon className="w-4 h-4" />
              </button>
            </div>
            <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-xs">
              <div className="flex items-center gap-1">
                <CalendarIcon className="w-3 h-3" />
                <span>{`${sessionDate.getMonth() + 1}/${sessionDate.getDate()}`}</span>
              </div>
              <div className="flex items-center gap-1">
                <ClockIcon className="w-3 h-3" />
                <span>
                  {sessionDate.toLocaleTimeString([], {
                    hour: 'numeric',
                    minute: '2-digit'
                  })}
                </span>
              </div>
              <div className="flex items-center gap-1 col-span-2">
                <CurrencyDollarIcon className="w-3 h-3" />
                <span>{number(snapshot.session_start_value)} USD</span>
              </div>
            </div>
          </div>
          <div className="text-sm">
            Goal: {number(snapshot.session_goal_value)} USD
          </div>
          <div
            className="w-full bg-gray-200 rounded-full h-2 overflow-hidden my-1"
          >
            <div
              className="bg-blue-500 h-2 rounded-full"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div
            className={`text-sm ${perfValue >= 0 ? 'text-green-600' : 'text-red-600'}`}
          >
            {perfValue >= 0 ? '+' : ''}
            {number(perfValue)} ({number(perfPct)}%)
          </div>
        </div>

        {/* BACK SIDE ------------------------------------------------------ */}
        <div
          className="absolute w-full h-full backface-hidden flex flex-col items-center justify-start p-2"
          style={{ backfaceVisibility: 'hidden', transform: 'rotateY(180deg)' }}
        >
          <div className="font-semibold">Edit Session</div>

          <div className="flex flex-col space-y-2 mt-1 w-11/12">
            <input
              type="date"
              className="border rounded px-2 py-1 text-sm"
              value={new Date(editableSnapshot.session_start_time)
                .toISOString()
                .substring(0, 10)}
              onChange={(e) =>
                handleInputChange('session_start_date', e.target.value)
              }
            />

            <input
              type="time"
              className="border rounded px-2 py-1 text-sm"
              value={new Date(editableSnapshot.session_start_time)
                .toTimeString()
                .substring(0, 5)}
              onChange={(e) =>
                handleInputChange('session_start_time', e.target.value)
              }
            />

            <input
              type="number"
              className="border rounded px-2 py-1 text-sm"
              value={editableSnapshot.session_start_value}
              onChange={(e) =>
                handleInputChange('session_start_value', e.target.value)
              }
            />

            <input
              type="number"
              className="border rounded px-2 py-1 text-sm"
              value={editableSnapshot.session_goal_value}
              onChange={(e) =>
                handleInputChange('session_goal_value', e.target.value)
              }
            />
          </div>

          <div className="flex flex-row space-x-2 mt-2">
            <button
              type="button"
              className="px-2 py-1 text-white bg-blue-600 rounded text-sm"
              onClick={handleSave}
            >
              Save
            </button>
            <button
              type="button"
              className="px-2 py-1 border rounded text-sm flex items-center gap-1"
              onClick={onReset}
            >
              <ArrowPathIcon className="w-4 h-4" />
              Reset
            </button>
          </div>

          <button
            type="button"
            className="mt-1 text-sm text-blue-600"
            onClick={flipCard}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

PortfolioSessionCard.propTypes = {
  snapshot: PropTypes.object,
  onEditStart: PropTypes.func,
  onReset: PropTypes.func
};
