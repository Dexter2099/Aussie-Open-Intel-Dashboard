import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { select } from 'd3-selection'
import { drag } from 'd3-drag'
import { forceCenter, forceLink, forceManyBody, forceSimulation } from 'd3-force'
import type { GraphData, GraphNode, GraphEdge } from '../types'
import { fetchGraph } from '../lib/api'

const SAMPLE_GRAPH: GraphData = {
  nodes: [
    { id: 'e1', label: 'Entity 1', kind: 'entity', type: 'Org' },
    { id: 'e2', label: 'Entity 2', kind: 'entity', type: 'Org' },
    { id: 'ev1', label: 'Event 1', kind: 'event', type: 't' },
  ],
  edges: [
    { source: 'e1', target: 'ev1', weight: 2 },
    { source: 'e2', target: 'ev1', weight: 1 },
  ],
}

export default function GraphPage() {
  const svgRef = useRef<SVGSVGElement>(null)
  const [data, setData] = useState<GraphData>(SAMPLE_GRAPH)
  const [selected, setSelected] = useState<GraphNode | null>(null)
  const [params] = useSearchParams()
  const entityId = params.get('entity_id') || ''

  useEffect(() => {
    async function load() {
      try {
        const res = await fetchGraph(entityId)
        setData(res.data)
      } catch {
        setData(SAMPLE_GRAPH)
      }
    }
    load()
  }, [entityId])

  useEffect(() => {
    if (!data) return
    const svg = select(svgRef.current)
    const width = Number(svg.attr('width'))
    const height = Number(svg.attr('height'))
    svg.selectAll('*').remove()

    const simulation = forceSimulation<GraphNode>(data.nodes)
      .force(
        'link',
        forceLink<GraphNode, GraphEdge>(data.edges).id((d) => d.id).distance(80)
      )
      .force('charge', forceManyBody().strength(-200))
      .force('center', forceCenter(width / 2, height / 2))

    const edge = svg
      .append('g')
      .attr('stroke', '#999')
      .attr('stroke-opacity', 0.6)
      .selectAll('line')
      .data(data.edges)
      .enter()
      .append('line')
      .attr('stroke-width', 1.5)

    edge.append('title').text((d) => `weight: ${d.weight}`)

    const node = svg
      .append('g')
      .selectAll('g')
      .data(data.nodes)
      .enter()
      .append('g')
      .call(
        drag<SVGGElement, GraphNode>()
          .on('start', (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart()
            d.fx = d.x
            d.fy = d.y
          })
          .on('drag', (event, d) => {
            d.fx = event.x
            d.fy = event.y
          })
          .on('end', (event, d) => {
            if (!event.active) simulation.alphaTarget(0)
            d.fx = null
            d.fy = null
          })
      )
      .on('mouseover', function () {
        select(this).selectAll('circle,rect').attr('stroke', '#000')
      })
      .on('mouseout', function () {
        if (selected && select(this).datum() === selected) return
        select(this).selectAll('circle,rect').attr('stroke', null)
      })
      .on('click', (_event, d) => {
        setSelected(d)
        node
          .selectAll('circle,rect')
          .attr('stroke', (n) => (n === d ? '#000' : null))
      })

    node.each(function (d) {
      if (d.kind === 'event') {
        select(this).append('circle').attr('r', 8).attr('fill', '#e53935')
      } else {
        select(this)
          .append('rect')
          .attr('x', -6)
          .attr('y', -6)
          .attr('width', 12)
          .attr('height', 12)
          .attr('fill', '#1e88e5')
      }
    })

    node.append('title').text((d) => d.label)

    simulation.on('tick', () => {
      edge
        .attr('x1', (d: any) => (typeof d.source === 'string' ? 0 : d.source.x))
        .attr('y1', (d: any) => (typeof d.source === 'string' ? 0 : d.source.y))
        .attr('x2', (d: any) => (typeof d.target === 'string' ? 0 : d.target.x))
        .attr('y2', (d: any) => (typeof d.target === 'string' ? 0 : d.target.y))

      node.attr('transform', (d) => `translate(${d.x},${d.y})`)
    })

    return () => simulation.stop()
  }, [data, selected])

  return (
    <>
      <svg
        ref={svgRef}
        width={800}
        height={600}
        style={{ border: '1px solid #ccc', width: '100%', height: '100vh' }}
      />
      <NodeDrawer node={selected} graph={data} onClose={() => setSelected(null)} />
    </>
  )
}

function NodeDrawer({
  node,
  graph,
  onClose,
}: {
  node: GraphNode | null
  graph: GraphData | null
  onClose: () => void
}) {
  const closeRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!node) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    closeRef.current?.focus()
    return () => document.removeEventListener('keydown', handler)
  }, [node, onClose])

  if (!node || !graph) return null

  const relatedIds = graph.edges
    .filter((e) => e.source === node.id || e.target === node.id)
    .map((e) => (e.source === node.id ? e.target : e.source))
  const related = relatedIds
    .map((id) => graph.nodes.find((n) => n.id === id)!)
    .filter(Boolean)

  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: 'fixed',
        top: 0,
        right: 0,
        width: '90%',
        maxWidth: '320px',
        height: '100%',
        background: '#fff',
        boxShadow: '-2px 0 8px rgba(0,0,0,0.2)',
        padding: '1rem',
        zIndex: 1000,
        overflowY: 'auto',
      }}
    >
      <button
        onClick={onClose}
        ref={closeRef}
        aria-label="Close"
        style={{
          float: 'right',
          background: 'none',
          border: 'none',
          fontSize: '1.5rem',
          cursor: 'pointer',
        }}
      >
        &times;
      </button>
      <h2 style={{ marginTop: 0 }}>{node.label}</h2>
      <div>ID: {node.id}</div>
      <div>Kind: {node.kind}</div>
      {node.type && <div>Type: {node.type}</div>}
      <div style={{ marginTop: '0.5rem' }}>Related:</div>
      <ul>
        {related.map((r) => (
          <li key={r.id}>
            {r.label} ({r.kind})
          </li>
        ))}
      </ul>
    </div>
  )
}
