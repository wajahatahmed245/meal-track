import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, PieChart, GaugeChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  MarkLineComponent,
  LegendComponent,
  GraphicComponent,
  DataZoomComponent,
  TitleComponent,
} from 'echarts/components'

use([
  CanvasRenderer,
  BarChart, LineChart, PieChart, GaugeChart,
  GridComponent, TooltipComponent, MarkLineComponent,
  LegendComponent, GraphicComponent, DataZoomComponent, TitleComponent,
])
