import useSWR from 'swr';
import axios from 'utils/axios';

/** GET /prices/history?asset=BTC&granularity=24 */
export function useGetPriceHistory(asset = 'BTC', granularity = '24') {
  const url = `/prices/history?asset=${asset}&granularity=${granularity}`;
  const { data, error, isLoading } = useSWR(url, (u) =>
    axios.get(u).then((r) => r.data)
  );
  return {
    history: data ?? [],
    historyLoading: isLoading,
    historyError: error
  };
}