import axios from 'utils/axios';

export async function runSonicCycle() {
  try {
    return await axios.post('/monitors/sonic_cycle');
  } catch (error) {
    console.error(error);
    throw error;
  }
}
