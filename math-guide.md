# Mathematics Complete Study Guide
**SAT 1 & EST 1 | Teacher: Ahmed Labib**

## Table of Contents
1. Algebra & Polynomials
2. Trigonometry
3. Logarithms & Exponentials
4. Calculus Basics
5. Geometry & Vectors

---

## 1. Algebra & Polynomials

### 1.1 Quadratic Equations

**Standard Form:** ax² + bx + c = 0

**Quadratic Formula:**
```
x = [-b ± √(b² - 4ac)] / 2a
```

**Discriminant:** Δ = b² - 4ac
- If Δ > 0: Two real roots
- If Δ = 0: One real root (repeated)
- If Δ < 0: No real roots (complex roots)

**Example Problem:**
Solve: 2x² - 8x + 6 = 0
- a = 2, b = -8, c = 6
- Δ = 64 - 48 = 16
- x = (8 ± 4)/4 = 3 or 1

### 1.2 Polynomial Operations

**Factorization Methods:**
1. Common factor: ax + bx = x(a + b)
2. Grouping: ax + ay + bx + by = a(x + y) + b(x + y)
3. Difference of squares: a² - b² = (a + b)(a - b)
4. Perfect square: a² + 2ab + b² = (a + b)²
5. Sum/Difference of cubes: a³ + b³ = (a + b)(a² - ab + b²)

### 1.3 Systems of Linear Equations

**Method 1: Substitution**
```
y = 2x + 3
x + y = 6
```
Substitute: x + (2x + 3) = 6 → 3x = 3 → x = 1, y = 5

**Method 2: Elimination**
```
2x + y = 7
x - y = 2
```
Add: 3x = 9 → x = 3, y = 1

### 1.4 Inequalities

**Properties:**
- a < b and b < c → a < c
- a < b → a + c < b + c
- a < b and c > 0 → ac < bc
- a < b and c < 0 → ac > bc (inequality reverses)

**Absolute Value Inequalities:**
- |x| < a → -a < x < a
- |x| > a → x < -a or x > a

---

## 2. Trigonometry

### 2.1 Basic Trigonometric Ratios

**In a Right Triangle:**
- sin θ = opposite/hypotenuse
- cos θ = adjacent/hypotenuse
- tan θ = opposite/adjacent

**Special Angles:**

| Angle | sin | cos | tan |
|-------|-----|-----|-----|
| 0°    | 0   | 1   | 0   |
| 30°   | 1/2 | √3/2 | 1/√3 |
| 45°   | √2/2 | √2/2 | 1   |
| 60°   | √3/2 | 1/2 | √3  |
| 90°   | 1   | 0   | ∞   |

### 2.2 Trigonometric Identities

**Fundamental:**
```
sin²θ + cos²θ = 1
1 + tan²θ = sec²θ
1 + cot²θ = csc²θ
```

**Sum and Difference:**
```
sin(A ± B) = sin A cos B ± cos A sin B
cos(A ± B) = cos A cos B ∓ sin A sin B
tan(A ± B) = (tan A ± tan B) / (1 ∓ tan A tan B)
```

**Double Angle:**
```
sin 2θ = 2 sin θ cos θ
cos 2θ = cos²θ - sin²θ = 2cos²θ - 1 = 1 - 2sin²θ
tan 2θ = 2 tan θ / (1 - tan²θ)
```

### 2.3 Trigonometric Equations

**Example:** Solve sin θ = 1/2, where 0° ≤ θ ≤ 360°
- θ = 30° or θ = 150°

**Example:** Solve cos θ = -√3/2, where 0 ≤ θ ≤ 2π
- θ = 5π/6 or θ = 7π/6

---

## 3. Logarithms & Exponentials

### 3.1 Logarithmic Properties

**Definition:** logₐ(x) = y ⟺ aʸ = x

**Properties:**
```
logₐ(mn) = logₐ(m) + logₐ(n)
logₐ(m/n) = logₐ(m) - logₐ(n)
logₐ(mⁿ) = n logₐ(m)
logₐ(a) = 1
logₐ(1) = 0
```

**Change of Base:**
```
logₐ(x) = logᵦ(x) / logᵦ(a)
```

### 3.2 Exponential Equations

**Solving:** 2ˣ = 8
- Take log: x log 2 = log 8
- x = log 8 / log 2 = 3

**Solving:** 3ˣ⁻¹ = 27
- 3ˣ⁻¹ = 3³
- x - 1 = 3
- x = 4

### 3.3 Growth and Decay

**Exponential Growth:** A(t) = A₀ · aᵗ
- A₀ = initial amount
- a = growth factor
- t = time

**Half-life:** A(t) = A₀ · (1/2)^(t/T)
- T = half-life period

---

## 4. Calculus Basics

### 4.1 Limits

**Definition:** lim(x→a) f(x) = L
- The function approaches L as x approaches a

**Properties:**
```
lim [f(x) + g(x)] = lim f(x) + lim g(x)
lim [f(x) · g(x)] = lim f(x) · lim g(x)
lim [f(x)/g(x)] = lim f(x) / lim g(x), if lim g(x) ≠ 0
```

### 4.2 Derivatives

**Definition:** f'(x) = lim(h→0) [f(x+h) - f(x)] / h

**Differentiation Rules:**

1. **Power Rule:** d/dx(xⁿ) = nxⁿ⁻¹
2. **Constant Rule:** d/dx(c) = 0
3. **Sum Rule:** d/dx[f(x) + g(x)] = f'(x) + g'(x)
4. **Product Rule:** d/dx[f(x)g(x)] = f'(x)g(x) + f(x)g'(x)
5. **Quotient Rule:** d/dx[f(x)/g(x)] = [f'(x)g(x) - f(x)g'(x)] / [g(x)]²
6. **Chain Rule:** d/dx[f(g(x))] = f'(g(x)) · g'(x)

**Common Derivatives:**
```
d/dx(eˣ) = eˣ
d/dx(ln x) = 1/x
d/dx(sin x) = cos x
d/dx(cos x) = -sin x
d/dx(tan x) = sec²x
```

### 4.3 Applications of Derivatives

**Critical Points:** Points where f'(x) = 0 or undefined
- Local maxima/minima occur at critical points

**Second Derivative Test:**
- If f''(x) > 0: local minimum
- If f''(x) < 0: local maximum
- If f''(x) = 0: inconclusive

**Example:** Find max/min of f(x) = x² - 4x + 3
- f'(x) = 2x - 4 = 0 → x = 2
- f''(x) = 2 > 0 → minimum at x = 2
- f(2) = 4 - 8 + 3 = -1 → minimum point (2, -1)

### 4.4 Integration

**Antiderivative:** ∫xⁿ dx = xⁿ⁺¹/(n+1) + C (n ≠ -1)

**Power Rule:** ∫xⁿ dx = xⁿ⁺¹/(n+1) + C

**Standard Integrals:**
```
∫eˣ dx = eˣ + C
∫(1/x) dx = ln|x| + C
∫sin x dx = -cos x + C
∫cos x dx = sin x + C
```

---

## 5. Geometry & Vectors

### 5.1 Conic Sections

**Circle:** (x - h)² + (y - k)² = r²
- Center: (h, k), Radius: r

**Ellipse:** (x²/a²) + (y²/b²) = 1
- Semi-major axis: a, Semi-minor axis: b

**Parabola:** y² = 4px or x² = 4py
- Vertex at origin, Focus at (p, 0) or (0, p)

**Hyperbola:** (x²/a²) - (y²/b²) = 1

### 5.2 Vectors

**Vector Addition:** A + B = (a₁ + b₁, a₂ + b₂)

**Scalar Multiplication:** kA = (ka₁, ka₂)

**Dot Product:** A · B = a₁b₁ + a₂b₂ = |A||B|cos θ

**Magnitude:** |A| = √(a₁² + a₂²)

**Cross Product (3D):**
```
A × B = |i    j    k  |
        |a₁   a₂   a₃ |
        |b₁   b₂   b₃ |
```

---

## Practice Problems

### Algebra
1. Solve: x² - 5x + 6 = 0
2. Factor: 2x³ - 8x
3. Solve: 2x + 3y = 7, x - y = 1

### Trigonometry
1. Find sin(45°)
2. Solve: sin x = √3/2, 0 ≤ x ≤ 2π
3. Verify: sin²x + cos²x = 1

### Calculus
1. Find derivative: f(x) = 3x² + 2x + 1
2. Find critical points: f(x) = x³ - 3x
3. Integrate: ∫(2x + 3) dx

---

**Study Tip:** Practice at least 10 problems daily from each section!
