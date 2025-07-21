
import React from 'react';
import { Card, CardContent, Typography, Avatar, Stack } from '@mui/material';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useSelector } from 'react-redux';

function Item({ item, columnId }) {
  const { profiles } = useSelector((state) => state.kanban);
  const assignee = profiles.find((p) => p.id === item.assignee);

  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({
    id: item.id,
    data: { type: 'CARD', sourceColumnId: columnId }
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    cursor: 'grab'
  };

  return (
    <Card ref={setNodeRef} style={style} elevation={1} {...attributes} {...listeners}>
      <CardContent sx={{ p: 1 }}>
        <Stack direction="row" spacing={1} alignItems="center">
          {assignee && <Avatar src={assignee.avatar} alt={assignee.name} sx={{ width: 24, height: 24 }} />}
          <Typography variant="body2">{item.content}</Typography>
        </Stack>
      </CardContent>
    </Card>
  );
}

export default Item;
