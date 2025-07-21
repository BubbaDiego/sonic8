
const kanbanData = {
  columnsOrder: ['backlog', 'todo', 'inprogress', 'review', 'done'],
  columns: [
    { id: 'backlog', title: 'Backlog', color: '#9e9e9e', wipLimit: null, itemIds: ['task-1', 'task-2'] },
    { id: 'todo', title: 'To Do', color: '#2196f3', wipLimit: 5, itemIds: ['task-3'] },
    { id: 'inprogress', title: 'In Progress', color: '#ff9800', wipLimit: 3, itemIds: ['task-4'] },
    { id: 'review', title: 'Review', color: '#9c27b0', wipLimit: 2, itemIds: [] },
    { id: 'done', title: 'Done', color: '#4caf50', wipLimit: null, itemIds: ['task-5'] }
  ],
  items: [
    { id: 'task-1', content: 'Initial project scaffolding', assignee: 'user-1', storyId: 'story-1' },
    { id: 'task-2', content: 'Install dependencies', assignee: 'user-1', storyId: 'story-1' },
    { id: 'task-3', content: 'Build Board UI', assignee: 'user-1', storyId: 'story-2' },
    { id: 'task-4', content: 'Implement drag‑and‑drop', assignee: 'user-1', storyId: 'story-2' },
    { id: 'task-5', content: 'Write integration docs', assignee: 'user-1', storyId: 'story-3' }
  ],
  profiles: [{ id: 'user-1', name: 'Bubba', avatar: '/static/images/bubba_icon.png' }],
  comments: [],
  userStoryOrder: ['story-1', 'story-2', 'story-3'],
  userStory: [
    { id: 'story-1', title: 'Project Setup', itemIds: ['task-1', 'task-2'] },
    { id: 'story-2', title: 'MVP Features', itemIds: ['task-3', 'task-4'] },
    { id: 'story-3', title: 'QA & Deployment', itemIds: ['task-5'] }
  ]
};

export default kanbanData;
