import axios from 'utils/axios';

export async function runFullCycle() {
  try {
    return await axios.post('/cyclone/run');
  } catch (error) {
    console.error(error);
    throw error;
  }
}

export async function runPriceUpdate() {
  try {
    return await axios.post('/cyclone/prices');
  } catch (error) {
    console.error(error);
    throw error;
  }
}

export async function runPositionUpdate() {
  try {
    return await axios.post('/cyclone/positions');
  } catch (error) {
    console.error(error);
    throw error;
  }
}

export async function deleteAllData() {
  try {
    return await axios.delete('/cyclone/data');
  } catch (error) {
    console.error(error);
    throw error;
  }
}
