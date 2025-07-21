import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'utils/axios';

const initialState = {
  columns: [],
  columnsOrder: [],
  items: [],
  profiles: [],
  comments: [],
  userStory: [],
  userStoryOrder: [],
  selectedItem: false
};

export const getColumns = createAsyncThunk('kanban/getColumns', async () => {
  const response = await axios.get('/api/kanban/columns');
  return response.data.columns;
});

export const getColumnsOrder = createAsyncThunk('kanban/getColumnsOrder', async () => {
  const response = await axios.get('/api/kanban/columns-order');
  return response.data.columnsOrder;
});

export const getItems = createAsyncThunk('kanban/getItems', async () => {
  const response = await axios.get('/api/kanban/items');
  return response.data.items;
});

export const getProfiles = createAsyncThunk('kanban/getProfiles', async () => {
  const response = await axios.get('/api/kanban/profiles');
  return response.data.profiles;
});

export const getUserStory = createAsyncThunk('kanban/getUserStory', async () => {
  const response = await axios.get('/api/kanban/userstory');
  return response.data.userStory;
});

export const getUserStoryOrder = createAsyncThunk('kanban/getUserStoryOrder', async () => {
  const response = await axios.get('/api/kanban/userstory-order');
  return response.data.userStoryOrder;
});

export const getComments = createAsyncThunk('kanban/getComments', async () => {
  const response = await axios.get('/api/kanban/comments');
  return response.data.comments;
});

export const updateColumnOrder = createAsyncThunk('kanban/updateColumnOrder', async (columnsOrder) => {
  const response = await axios.post('/api/kanban/update-column-order', { columnsOrder });
  return response.data.columnsOrder;
});

export const updateColumnItemOrder = createAsyncThunk('kanban/updateColumnItemOrder', async (columns) => {
  const response = await axios.post('/api/kanban/update-item-order', { columns });
  return response.data.columns;
});

const kanbanSlice = createSlice({
  name: 'kanban',
  initialState,
  reducers: {
    selectItem(state, action) {
      state.selectedItem = action.payload;
    },
    addColumn(state, action) {
      const { column } = action.payload;
      state.columns.push(column);
      state.columnsOrder.push(column.id);
    },
    editColumn(state, action) {
      const { column } = action.payload;
      const idx = state.columns.findIndex((c) => c.id === column.id);
      if (idx > -1) state.columns[idx] = column;
    },
    deleteColumn(state, action) {
      const { columnId } = action.payload;
      state.columns = state.columns.filter((c) => c.id !== columnId);
      state.columnsOrder = state.columnsOrder.filter((id) => id !== columnId);
    },
    addItem(state, action) {
      const { columnId, item, storyId } = action.payload;
      state.items.push(item);
      const column = state.columns.find((c) => c.id === columnId);
      if (column) column.itemIds.push(item.id);
      if (storyId && storyId !== '0') {
        const story = state.userStory.find((s) => s.id === storyId);
        if (story) story.itemIds.push(item.id);
      }
    },
    editItem(state, action) {
      const { columnId, item, storyId } = action.payload;
      const oldColumn = state.columns.find((c) => c.itemIds.includes(item.id));
      if (oldColumn && oldColumn.id !== columnId) {
        oldColumn.itemIds = oldColumn.itemIds.filter((id) => id !== item.id);
      }
      const newColumn = state.columns.find((c) => c.id === columnId);
      if (newColumn && !newColumn.itemIds.includes(item.id)) {
        newColumn.itemIds.push(item.id);
      }
      const oldStory = state.userStory.find((s) => s.itemIds.includes(item.id));
      if (oldStory && oldStory.id !== storyId) {
        oldStory.itemIds = oldStory.itemIds.filter((id) => id !== item.id);
      }
      if (storyId && storyId !== '0') {
        const newStory = state.userStory.find((s) => s.id === storyId);
        if (newStory && !newStory.itemIds.includes(item.id)) {
          newStory.itemIds.push(item.id);
        }
      }
      const idx = state.items.findIndex((i) => i.id === item.id);
      if (idx > -1) state.items[idx] = item;
    },
    deleteItem(state, action) {
      const { itemId } = action.payload;
      state.items = state.items.filter((i) => i.id !== itemId);
      state.columns.forEach((c) => {
        c.itemIds = c.itemIds.filter((id) => id !== itemId);
      });
      state.userStory.forEach((s) => {
        s.itemIds = s.itemIds.filter((id) => id !== itemId);
      });
    },
    addItemComment(state, action) {
      const { itemId, comment } = action.payload;
      state.comments.push(comment);
      const item = state.items.find((i) => i.id === itemId);
      if (item) {
        if (!item.commentIds) item.commentIds = [];
        item.commentIds.push(comment.id);
      }
    },
    addStory(state, action) {
      const { story } = action.payload;
      state.userStory.push(story);
      state.userStoryOrder.push(story.id);
    },
    editStory(state, action) {
      const { story } = action.payload;
      const idx = state.userStory.findIndex((s) => s.id === story.id);
      if (idx > -1) state.userStory[idx] = story;
    },
    deleteStory(state, action) {
      const { storyId } = action.payload;
      state.userStory = state.userStory.filter((s) => s.id !== storyId);
      state.userStoryOrder = state.userStoryOrder.filter((id) => id !== storyId);
    },
    addStoryComment(state, action) {
      const { storyId, comment } = action.payload;
      state.comments.push(comment);
      const story = state.userStory.find((s) => s.id === storyId);
      if (story) {
        if (!story.commentIds) story.commentIds = [];
        story.commentIds.push(comment.id);
      }
    },
    updateStoryOrder(state, action) {
      state.userStoryOrder = action.payload;
    },
    updateStoryItemOrder(state, action) {
      state.userStory = action.payload;
    }
  },
  extraReducers: (builder) => {
    builder
      .addCase(getColumns.fulfilled, (state, action) => {
        state.columns = action.payload;
      })
      .addCase(getColumnsOrder.fulfilled, (state, action) => {
        state.columnsOrder = action.payload;
      })
      .addCase(getItems.fulfilled, (state, action) => {
        state.items = action.payload;
      })
      .addCase(getProfiles.fulfilled, (state, action) => {
        state.profiles = action.payload;
      })
      .addCase(getUserStory.fulfilled, (state, action) => {
        state.userStory = action.payload;
      })
      .addCase(getUserStoryOrder.fulfilled, (state, action) => {
        state.userStoryOrder = action.payload;
      })
      .addCase(getComments.fulfilled, (state, action) => {
        state.comments = action.payload;
      })
      .addCase(updateColumnOrder.fulfilled, (state, action) => {
        state.columnsOrder = action.payload;
      })
      .addCase(updateColumnItemOrder.fulfilled, (state, action) => {
        state.columns = action.payload;
      });
  }
});

// wrapper action creators to match component calls
export const selectItem = (itemId) => (dispatch) => {
  dispatch(kanbanSlice.actions.selectItem(itemId));
};
export const addColumn = (column, _columns, _order) => (dispatch) => {
  dispatch(kanbanSlice.actions.addColumn({ column }));
};
export const editColumn = (column) => (dispatch) => {
  dispatch(kanbanSlice.actions.editColumn({ column }));
};
export const deleteColumn = (columnId) => (dispatch) => {
  dispatch(kanbanSlice.actions.deleteColumn({ columnId }));
};
export const addItem = (columnId, _cols, item, _items, storyId) => (dispatch) => {
  dispatch(kanbanSlice.actions.addItem({ columnId, item, storyId }));
};
export const editItem = (columnId, _cols, item, _items, storyId) => (dispatch) => {
  dispatch(kanbanSlice.actions.editItem({ columnId, item, storyId }));
};
export const deleteItem = (itemId) => (dispatch) => {
  dispatch(kanbanSlice.actions.deleteItem({ itemId }));
};
export const addItemComment = (itemId, comment) => (dispatch) => {
  dispatch(kanbanSlice.actions.addItemComment({ itemId, comment }));
};
export const addStory = (story) => (dispatch) => {
  dispatch(kanbanSlice.actions.addStory({ story }));
};
export const editStory = (story) => (dispatch) => {
  dispatch(kanbanSlice.actions.editStory({ story }));
};
export const deleteStory = (storyId) => (dispatch) => {
  dispatch(kanbanSlice.actions.deleteStory({ storyId }));
};
export const addStoryComment = (storyId, comment) => (dispatch) => {
  dispatch(kanbanSlice.actions.addStoryComment({ storyId, comment }));
};
export const updateStoryOrder = (order) => (dispatch) => {
  dispatch(kanbanSlice.actions.updateStoryOrder(order));
};
export const updateStoryItemOrder = (stories) => (dispatch) => {
  dispatch(kanbanSlice.actions.updateStoryItemOrder(stories));
};

export default kanbanSlice.reducer;
