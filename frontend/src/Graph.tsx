import React, { useEffect, useRef } from 'react'
import * as d3 from 'd3'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export default function Graph() {
  const ref = useRef<SVGSVGElement | null>(null)

  useEffect(() => {
    fetch(`${API_BASE}/graph`)
      .then(r => r.json())
      .then(data => {
        const svg = d3.select(ref.current)
        svg.selectAll('*').remove()
        const width = 600
        const height = 400
        svg.attr('viewBox', `0 0 ${width} ${height}`)

        const link = svg.append('g')
          .selectAll('line')
          .data(data.links || [])
          .enter()
          .append('line')
          .attr('stroke', '#999')

        const node = svg.append('g')
          .selectAll('circle')
          .data(data.nodes || [])
          .enter()
          .append('circle')
          .attr('r', 5)
          .attr('fill', 'steelblue')

        const simulation = d3.forceSimulation(data.nodes)
          .force('link', d3.forceLink(data.links).id((d: any) => d.id))
          .force('charge', d3.forceManyBody().strength(-200))
          .force('center', d3.forceCenter(width / 2, height / 2))

        simulation.on('tick', () => {
          link
            .attr('x1', (d: any) => d.source.x)
            .attr('y1', (d: any) => d.source.y)
            .attr('x2', (d: any) => d.target.x)
            .attr('y2', (d: any) => d.target.y)
          node
            .attr('cx', (d: any) => d.x)
            .attr('cy', (d: any) => d.y)
        })
      })
      .catch(console.error)
  }, [])

  return <svg ref={ref} style={{ width: '100%', height: '100%' }} />
}
