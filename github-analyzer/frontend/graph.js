// D3.js Force Directed Graph Simulation
const width = window.innerWidth;
const height = window.innerHeight;

const svg = d3.select("#graph-container")
    .append("svg")
    .attr("width", width)
    .attr("height", height);

const simulation = d3.forceSimulation()
    .force("link", d3.forceLink().id(d => d.id).distance(100))
    .force("charge", d3.forceManyBody().strength(-300))
    .force("center", d3.forceCenter(width / 2, height / 2));

const nodes = [
    { id: "Database", group: 1 },
    { id: "AppLogic", group: 2 },
    { id: "UserAPI", group: 2 },
    { id: "Frontend", group: 3 }
];

const links = [
    { source: "AppLogic", target: "Database" },
    { source: "UserAPI", target: "AppLogic" },
    { source: "Frontend", target: "UserAPI" }
];

const link = svg.append("g")
    .selectAll("line")
    .data(links)
    .enter().append("line")
    .attr("stroke", "#475569")
    .attr("stroke-width", 2);

const node = svg.append("g")
    .selectAll("circle")
    .data(nodes)
    .enter().append("circle")
    .attr("r", 10)
    .attr("fill", d => d.group === 1 ? "#ef4444" : d.group === 2 ? "#6366f1" : "#10b981")
    .call(d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended));

node.append("title").text(d => d.id);

simulation.nodes(nodes).on("tick", () => {
    link.attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);

    node.attr("cx", d => d.x)
        .attr("cy", d => d.y);
});

simulation.force("link").links(links);

function dragstarted(event) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    event.subject.fx = event.subject.x;
    event.subject.fy = event.subject.y;
}

function dragged(event) {
    event.subject.fx = event.x;
    event.subject.fy = event.y;
}

function dragended(event) {
    if (!event.active) simulation.alphaTarget(0);
    event.subject.fx = null;
    event.subject.fy = null;
}
