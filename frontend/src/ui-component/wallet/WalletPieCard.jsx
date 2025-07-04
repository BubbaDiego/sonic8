import React, { useState } from 'react';
import ReactApexChart from 'react-apexcharts';

const WalletPieCard = ({ data }) => {
  const [mode, setMode] = useState('pie');
  if (!data) return null;

  const options = {
    chart: { type: mode },
    labels: data.labels,
    colors: data.labels.map((l,i)=> data.colors[l] || ['#2ecc71','#e74c3c','#3498db'][i%3]),
    legend: { position: 'bottom' },
    tooltip: { y: { formatter: (val) => `${val}%` } }
  };

  return (
    <div onClick={()=> setMode((m)=> m==='pie'?'donut':'pie')} style={{cursor:'pointer'}}>
      <ReactApexChart options={options} series={data.series} type={mode} height={260}/>
    </div>
  );
};

export default WalletPieCard;
