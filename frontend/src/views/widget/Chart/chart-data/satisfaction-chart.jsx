// ==============================|| WIDGET - SATISFACTION CHART ||============================== //

const chartData = {
  height: 280,
  type: 'pie',
  options: {
    chart: {
      id: 'satisfaction-chart'
    },
    labels: ['extremely Satisfied', 'Satisfied', 'Poor', 'Very Poor'],
    legend: {
      show: true,
      position: 'bottom',
      fontFamily: 'inherit',
      labels: {
        colors: 'inherit'
      }
    },
    dataLabels: {
      enabled: true,
      dropShadow: {
        enabled: false
      }
    }
  },
  series: [66, 50, 40, 30]
};

export default chartData;
