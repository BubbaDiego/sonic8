
import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Stack, Chip } from '@mui/material';
import { DndContext, closestCorners } from '@dnd-kit/core';
import { SortableContext, horizontalListSortingStrategy, arrayMove } from '@dnd-kit/sortable';

import Column from './Column';
import {
  getColumns,
  getColumnsOrder,
  getItems,
  getUserStory,
  getUserStoryOrder,
  updateColumnOrder,
  updateColumnItemOrder
} from 'store/slices/kanban';

function Board() {
  const dispatch = useDispatch();
  const { columnsOrder, columns, userStory, userStoryOrder } = useSelector((state) => state.kanban);
  const [selectedStory, setSelectedStory] = useState('all');

  useEffect(() => {
    dispatch(getColumns());
    dispatch(getColumnsOrder());
    dispatch(getItems());
    dispatch(getUserStory());
    dispatch(getUserStoryOrder());
  }, [dispatch]);

  const handleDragEnd = ({ active, over }) => {
    if (!over || active.id === over.id) return;

    // COLUMN reorder
    if (active.data.current?.type === 'COLUMN') {
      const oldIndex = columnsOrder.indexOf(active.id);
      const newIndex = columnsOrder.indexOf(over.id);
      const newOrder = arrayMove(columnsOrder, oldIndex, newIndex);
      dispatch(updateColumnOrder(newOrder));
      return;
    }

    // CARD reorder inside same column
    const sourceColId = active.data.current?.sourceColumnId;
    const targetColId = over.data.current?.sourceColumnId;

    if (!sourceColId || !targetColId) return;

    if (sourceColId === targetColId) {
      const col = columns.find((c) => c.id === sourceColId);
      const oldIdx = col.itemIds.indexOf(active.id);
      const newIdx = col.itemIds.indexOf(over.id);
      const updatedColumn = {
        ...col,
        itemIds: arrayMove(col.itemIds, oldIdx, newIdx)
      };
      const newColumns = columns.map((c) => (c.id === col.id ? updatedColumn : c));
      dispatch(updateColumnItemOrder(newColumns));
    }
  };

  const filteredItemIds =
    selectedStory === 'all'
      ? null
      : userStory.find((s) => s.id === selectedStory)?.itemIds ?? [];

  return (
    <>
      <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
        <Chip
          label="All"
          color={selectedStory === 'all' ? 'primary' : 'default'}
          onClick={() => setSelectedStory('all')}
        />
        {userStoryOrder.map((sid) => {
          const story = userStory.find((s) => s.id === sid);
          return (
            <Chip
              key={sid}
              label={story.title}
              color={selectedStory === sid ? 'primary' : 'default'}
              onClick={() => setSelectedStory(sid)}
            />
          );
        })}
      </Stack>

      <DndContext collisionDetection={closestCorners} onDragEnd={handleDragEnd}>
        <SortableContext items={columnsOrder} strategy={horizontalListSortingStrategy}>
          <Stack direction="row" spacing={3} alignItems="flex-start">
            {columnsOrder.map((colId) => (
              <Column key={colId} id={colId} filterItemIds={filteredItemIds} />
            ))}
          </Stack>
        </SortableContext>
      </DndContext>
    </>
  );
}

export default Board;
