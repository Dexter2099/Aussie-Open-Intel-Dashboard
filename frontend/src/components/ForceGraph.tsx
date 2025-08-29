import React, { useEffect, useRef } from 'react'
import * as d3 from 'd3'

type Node = { id: number; label: string }
type Edge = { src: number; dst: number; relation: string }

type Props = {
  apiBase: string
  seed?: number | null
}

export default function ForceGraph({ apiBase, seed = null }: Props) {
  const ref = useRef<SVGSVGElement | null>(null)
  const width = 800
  const height = 500

  useEffect(() => {
    let destroyed = false
    const run = async () => {
      const params = new URLSearchParams()
      if (seed) params.set('seed', String(seed))
      const res = await fetch(`${apiBase}/graph?${params.toString()}`)
      const data = await res.json()
      if (destroyed) return
      renderGraph(data.nodes || [], data.edges || [])
    }
    run()
    return () => { destroyed = true }
  }, [apiBase, seed])

  function renderGraph(nodes: Node[], edges: Edge[]) {
    const svg = d3.select(ref.current!)
    svg.selectAll('*').remove()

    const sim = d3.forceSimulation(nodes as any)
      .force('charge', d3.forceManyBody().strength(-200))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('link', d3.forceLink(edges as any).id((d: any) => d.id).distance(120))

    const link = svg.append('g')
      .attr('stroke', '#aaa')
      .attr('stroke-width', 1.5)
      .selectAll('line')
      .data(edges)
      .enter().append('line')

    const node = svg.append('g')
      .selectAll('g')
      .data(nodes)
      .enter().append('g')

    node.append('circle')
      .attr('r', 10)
      .attr('fill', '#4fc3f7')
      .attr('stroke', '#1e88e5')

    node.append('text')
      .text((d: any) => d.label)
      .attr('x', 12)
      .attr('y', 4)
      .attr('font-size', 10)
      .attr('fill', '#333')

    sim.on('tick', () => {
      link
        .attr('x1', (d: any) => (d.source.x))
        .attr('y1', (d: any) => (d.source.y))
        .attr('x2', (d: any) => (d.target.x))
        .attr('y2', (d: any) => (d.target.y))

      node.attr('transform', (d: any) => `translate(${d.x},${d.y})`)
    })
  }

  return (
    <div style={{ height: '100%', display: 'grid', gridTemplateRows: '40px 1fr' }}>
      <div style={{ padding: '8px 12px', borderBottom: '1px solid #eee' }}>Graph</div>
      <svg ref={ref} width={width} height={height} />
    </div>
  )
}

