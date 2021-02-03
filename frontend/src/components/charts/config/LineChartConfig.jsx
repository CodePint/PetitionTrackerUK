const chartConfig = {
  type: "line",
  data: {
    labels: [],
    datasets: [
      {
        data: [],
      },
    ],
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    legend: {
      display: false,
    },
    scales: {
      xAxes: [
        {
          display: true,
          type: "time",
          ticks: {
            fontSize: 10,
          },
          time: {
            parser: "DD-MM-YYTHH:mm",
            displayFormats: {
              hour: "DD-MM-YYTHH:mm",
              minute: "DD-MM-YYTHH:mm",
              second: "DD-MM-YYTHH:mm",
              day: "DD-MM-YY",
              week: "DD-MM-YY",
              month: "MM-YYYY",
              year: "MM-YYYY",
            },
          },
        },
      ],
      yAxes: [
        {
          ticks: {
            fontSize: 10,
            precision: 0,
          },
        },
      ],
    },
  },
};

const dataConfig = {
  fill: false,
  pointRadius: 1,
  pointHoverRadius: 20,
  borderWidth: 3,
};

const chartColors = {
  cyan: "#00ffff",
  darkgrey: "#a9a9a9",
  darksalmon: "#e9967a",
  gold: "#ffd700",
  green: "#008000",
  lime: "#00ff00",
  magenta: "#ff00ff",
  maroon: "#800000",
  orange: "#ffa500",
  pink: "#ffc0cb",
};

export { chartConfig, dataConfig, chartColors };
