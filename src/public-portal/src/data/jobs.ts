export type Job = {
  id: string;
  title: string;
  team: string;
  location: string;
  workplace: "Remote" | "Hybrid" | "On-site";
  type: "Full-time" | "Contract";
  summary: string;
  description: string;
  responsibilities: string[];
  qualifications: string[];
  preferred: string[];
  posted: string;
  featured?: boolean;
};

export const jobs: Job[] = [
  {
    id: "senior-product-designer",
    title: "Senior Product Designer",
    team: "Product & Design",
    location: "Seattle, WA",
    workplace: "Hybrid",
    type: "Full-time",
    summary: "Shape intuitive, human-centered experiences for the next generation of intelligent workplace tools.",
    description: "You will partner with product, engineering, and research to turn complex workflows into clear, thoughtful experiences. This role is ideal for a systems thinker who cares deeply about craft and measurable customer outcomes.",
    responsibilities: [
      "Lead end-to-end product design from discovery through delivery.",
      "Translate customer insights into flows, prototypes, and polished interfaces.",
      "Partner with engineering to maintain quality through implementation.",
      "Contribute patterns and guidance to our evolving design system.",
    ],
    qualifications: [
      "5+ years designing digital products or equivalent practical experience.",
      "A portfolio demonstrating interaction design and systems thinking.",
      "Strong communication and cross-functional collaboration skills.",
    ],
    preferred: ["Experience with enterprise software.", "Familiarity with responsible AI design patterns."],
    posted: "2 days ago",
    featured: true,
  },
  {
    id: "ai-solutions-engineer",
    title: "AI Solutions Engineer",
    team: "Engineering",
    location: "New York, NY",
    workplace: "Hybrid",
    type: "Full-time",
    summary: "Build reliable AI-powered product experiences and help establish the engineering patterns behind them.",
    description: "You will build customer-facing AI capabilities and the systems that make them dependable. You will collaborate with product teams to move from prototypes to observable, evaluated experiences.",
    responsibilities: [
      "Build and maintain AI-assisted application features.",
      "Design evaluation, tracing, and quality-monitoring workflows.",
      "Create reusable integrations and engineering guidance.",
      "Review architecture and mentor engineers across the organization.",
    ],
    qualifications: [
      "4+ years of software engineering experience.",
      "Proficiency in Python or TypeScript and cloud-native development.",
      "Experience shipping and operating customer-facing services.",
    ],
    preferred: ["Experience with Azure AI Foundry.", "Knowledge of retrieval and agent orchestration patterns."],
    posted: "3 days ago",
    featured: true,
  },
  {
    id: "customer-success-lead",
    title: "Customer Success Lead",
    team: "Customer Experience",
    location: "United States",
    workplace: "Remote",
    type: "Full-time",
    summary: "Help strategic customers realize value, build durable partnerships, and bring their voice into our roadmap.",
    description: "You will own the post-sale relationship for a portfolio of strategic customers. You will turn business goals into practical adoption plans and coordinate the right team to deliver lasting outcomes.",
    responsibilities: [
      "Create and lead customer success plans with measurable outcomes.",
      "Coordinate executive reviews, adoption programs, and risk mitigation.",
      "Represent customer feedback in product planning conversations.",
      "Develop repeatable practices for a growing success organization.",
    ],
    qualifications: [
      "6+ years in customer success, consulting, or account leadership.",
      "Experience managing complex enterprise relationships.",
      "Excellent facilitation, storytelling, and problem-solving skills.",
    ],
    preferred: ["Experience with SaaS or AI products.", "Background in organizational change management."],
    posted: "5 days ago",
    featured: true,
  },
  {
    id: "product-marketing-manager",
    title: "Product Marketing Manager",
    team: "Marketing",
    location: "San Francisco, CA",
    workplace: "Hybrid",
    type: "Full-time",
    summary: "Define compelling product narratives and help teams bring new capabilities to market.",
    description: "You will connect customer insight, product strategy, and go-to-market execution. You will develop clear positioning and equip teams to tell differentiated product stories.",
    responsibilities: ["Own positioning and messaging for key product areas.", "Plan launches with product, sales, and communications.", "Develop customer evidence and enablement content."],
    qualifications: ["4+ years in product marketing or related roles.", "Strong writing and analytical skills.", "Experience leading cross-functional launches."],
    preferred: ["Enterprise technology experience.", "Understanding of AI market trends."],
    posted: "1 week ago",
  },
  {
    id: "frontend-engineer",
    title: "Frontend Engineer",
    team: "Engineering",
    location: "Austin, TX",
    workplace: "Remote",
    type: "Full-time",
    summary: "Create fast, accessible interfaces that make sophisticated technology feel effortless.",
    description: "You will build the component systems and product surfaces used by customers every day, working closely with designers and API engineers from idea to production.",
    responsibilities: ["Build accessible React product experiences.", "Improve performance and frontend architecture.", "Contribute reusable components and testing practices."],
    qualifications: ["3+ years with React and TypeScript.", "Strong knowledge of web accessibility and responsive design.", "Experience testing modern web applications."],
    preferred: ["Next.js experience.", "Experience with design systems."],
    posted: "1 week ago",
  },
  {
    id: "design-researcher",
    title: "Design Researcher",
    team: "Product & Design",
    location: "London, UK",
    workplace: "Hybrid",
    type: "Contract",
    summary: "Turn customer needs and behaviors into insights that guide responsible product decisions.",
    description: "You will plan and conduct generative and evaluative research across emerging product experiences, helping teams build a deep and shared understanding of customers.",
    responsibilities: ["Plan mixed-method research studies.", "Synthesize findings into clear opportunities.", "Partner with design and product throughout delivery."],
    qualifications: ["3+ years conducting product research.", "Strong interviewing and synthesis skills.", "A portfolio of applied research outcomes."],
    preferred: ["Research experience in emerging technology.", "Knowledge of inclusive research practices."],
    posted: "2 weeks ago",
  },
];

export function getJob(id: string): Job | undefined {
  return jobs.find((job) => job.id === id);
}
