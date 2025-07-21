
import axios from './axios';
import AxiosMockAdapter from 'axios-mock-adapter';
import initialData from '../__mocks__/kanbanData';

const STORAGE_KEY = 'kanbanData';

function loadData() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) return JSON.parse(stored);
  } catch (err) {
    console.error(err);
  }
  return JSON.parse(JSON.stringify(initialData));
}

function saveData(data) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch (err) {
    console.error(err);
  }
}

const data = loadData();
saveData(data); // ensure present

const mock = new AxiosMockAdapter(axios, { delayResponse: 200 });

// === GET endpoints ===
mock.onGet('/api/kanban/columns').reply(200, { columns: data.columns });
mock.onGet('/api/kanban/columns-order').reply(200, { columnsOrder: data.columnsOrder });
mock.onGet('/api/kanban/items').reply(200, { items: data.items });
mock.onGet('/api/kanban/profiles').reply(200, { profiles: data.profiles });
mock.onGet('/api/kanban/userstory').reply(200, { userStory: data.userStory });
mock.onGet('/api/kanban/userstory-order').reply(200, { userStoryOrder: data.userStoryOrder });
mock.onGet('/api/kanban/comments').reply(200, { comments: data.comments });

// === POST endpoints (partial) ===
mock.onPost('/api/kanban/update-column-order').reply((config) => {
  const { columnsOrder } = JSON.parse(config.data);
  data.columnsOrder = columnsOrder;
  saveData(data);
  return [200, { columnsOrder }];
});

mock.onPost('/api/kanban/update-item-order').reply((config) => {
  const { columns } = JSON.parse(config.data);
  data.columns = columns;
  saveData(data);
  return [200, { columns }];
});

// Add more endpoint mocks as needed ...

export default mock;
