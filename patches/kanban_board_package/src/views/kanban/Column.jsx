
import React from 'react';
import { Paper, Typography, Stack, IconButton } from '@mui/material';
import { useSelector } from 'react-redux';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import Item from './Item';
import AddIcon from '@mui/icons-material/Add';

function Column({ id, filterItemIds }) {
  const { columns, items } = useSelector((state) => state.kanban);
  const column = columns.find((c) => c.id === id);
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({
    id,
    data: { type: 'COLUMN' }
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition
  };

  const visibleItemIds = filterItemIds
    ? column.itemIds.filter((iid) => filterItemIds.includes(iid))
    : column.itemIds;

  return (
    <Paper
      ref={setNodeRef}
      style={style}
      sx={{ p: 1, width: 260, bgcolor: column.color + '22' }}
      {...attributes}
      {...listeners}
    >
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}>
        <Typography variant="subtitle2">
          {column.title}{' '}
          {column.wipLimit ? `(${visibleItemIds.length}/${column.wipLimit})` : `(${visibleItemIds.length})`}
        </Typography>
        <IconButton size="small" disabled>
          <AddIcon fontSize="inherit" />
        </IconButton>
      </Stack>
      <Stack spacing={1}>
        {visibleItemIds.map((itemId) => {
          const item = items.find((i) => i.id === itemId);
          return <Item key={itemId} item={item} columnId={column.id} />;
        })}
      </Stack>
    </Paper>
  );
}

export default Column;
