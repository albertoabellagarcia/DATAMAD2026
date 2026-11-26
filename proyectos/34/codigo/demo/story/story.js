(() => {
  const root = document.getElementById("story"), g = window.gsap, ST = window.ScrollTrigger
  if (!root || !g || !ST || matchMedia("(prefers-reduced-motion: reduce)").matches) return
  g.registerPlugin(ST)
  root.classList.add("story-js")
  const $$ = s => [...root.querySelectorAll(s)]
  const at = (trigger, start = "top 72%") => ({ trigger, start, toggleActions: "play none none reverse" })

  g.fromTo($$(".story-sign span"), { color: "#22364a" }, { color: "#ffcf4a", duration: .12, ease: "none", stagger: .07, scrollTrigger: at(".story-roof", "top 85%") })

  const f3 = root.querySelector(".story-f3")
  const t3 = g.timeline({ scrollTrigger: at(f3) })
  $$(".story-f3 .story-bal").forEach((b, i) => {
    const l = b.querySelector(".story-light")
    if (l) t3.fromTo(l, { opacity: 0 }, { opacity: 1, duration: .3, ease: "power2.out" }, i * .3)
    t3.fromTo(b.querySelector(".story-blind"), { scaleY: 1 }, { scaleY: .32, duration: .7, ease: "power3.out", transformOrigin: "50% 0%" }, i * .3 + .05)
  })

  // 2º: las ventanas se encienden con el desplazamiento, del alquiler más bajo al más alto,
  // y el tablero cuenta las encendidas. Al pasar la planta queda en el total.
  const glass = $$(".story-w-fit .story-w-glass"), flaps = root.querySelector(".story-flaps")
  const total = +flaps.dataset.n, cells = [...flaps.children], pad = String(total).length
  const show = n => { const d = String(n).padStart(pad, " "); cells.forEach((c, i) => { if (c.textContent !== d[i]) { c.textContent = d[i]; g.fromTo(c, { rotateX: -70 }, { rotateX: 0, duration: .22, ease: "power2.out" }) } }) }
  const count = { n: 0 }
  const t2 = g.timeline({ scrollTrigger: { trigger: ".story-f2", start: "top 65%", endTrigger: ".story-tally", end: "bottom 82%", scrub: .6 } })
  t2.fromTo(glass, { fill: "#0a1520" }, { fill: "#ffcf4a", duration: .2, ease: "none", stagger: 1.6 / glass.length }, 0)
    .fromTo(count, { n: 0 }, { n: total, duration: 1.8, ease: "none", onUpdate: () => show(Math.round(count.n)) }, 0)
    .fromTo($$(".story-w-blind"), { scaleY: .12 }, { scaleY: 1, duration: .3, ease: "power2.out", stagger: .01 }, 1.4)
  show(0)

  // Cada planta entra con un muelle corto: solo transform y opacity.
  $$(".story-room").forEach(r => g.from(r.children, { y: 28, opacity: 0, duration: .7, ease: "expo.out", stagger: .06, scrollTrigger: { trigger: r, start: "top 82%", once: true } }))

  // Buzones: se abren a mano (details); la trampilla y la carta las mueve el CSS.

  g.fromTo(".story-toldo", { scaleY: .12 }, { scaleY: 1, duration: .5, ease: "power3.out", scrollTrigger: at(".story-f0", "top 80%") })
  g.fromTo(".story-shutter", { yPercent: 0 }, { yPercent: -101, ease: "none", scrollTrigger: { trigger: ".story-shop-in", start: "top 78%", end: "top 30%", scrub: .5 } })

  const scrub = { trigger: ".story-doorway", start: "top 95%", end: "top 45%", scrub: .5 }
  g.fromTo(".story-leaf-l", { rotateY: 0 }, { rotateY: -82, ease: "none", scrollTrigger: scrub })
  g.fromTo(".story-leaf-r", { rotateY: 0 }, { rotateY: 82, ease: "none", scrollTrigger: { ...scrub } })
  root.querySelector(".story-go").addEventListener("focus", e => e.target.scrollIntoView({ block: "center" }))
})()
