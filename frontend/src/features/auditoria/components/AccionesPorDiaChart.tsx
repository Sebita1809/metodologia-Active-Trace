import ReactApexChart from 'react-apexcharts'
import type { ApexOptions } from 'apexcharts'
import type { AccionesPorDiaItem } from '../types'

interface AccionesPorDiaChartProps {
  items: AccionesPorDiaItem[]
}

export function AccionesPorDiaChart({ items }: AccionesPorDiaChartProps) {
  if (items.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-sm text-gray-400">
        Sin datos en el rango seleccionado.
      </div>
    )
  }

  const categories = items.map((i) => i.dia.slice(5, 10)) // MM-DD
  const seriesData = items.map((i) => i.total)

  const options: ApexOptions = {
    chart: {
      type: 'bar',
      toolbar: { show: false },
      animations: { enabled: false },
    },
    plotOptions: {
      bar: { borderRadius: 3, columnWidth: '60%' },
    },
    dataLabels: { enabled: false },
    xaxis: {
      categories,
      labels: { style: { fontSize: '10px' } },
    },
    yaxis: {
      labels: { style: { fontSize: '11px' } },
      title: { text: 'Acciones' },
    },
    colors: ['#3b82f6'],
    tooltip: {
      y: { formatter: (val: number) => `${val} acciones` },
    },
    grid: { borderColor: '#f1f5f9' },
  }

  const series = [{ name: 'Acciones', data: seriesData }]

  return (
    <ReactApexChart
      type="bar"
      options={options}
      series={series}
      height={200}
    />
  )
}
