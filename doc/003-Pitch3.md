A simpler approach: rather than handle joins with an `Object` type, instead
create a union with a special tag that allows for dynamic dispatch on all 
disjunctands of the union using a hash-map of symbols to field offsets.

E.g. unifying an Int and a Float produces a Float, so we treat Int as a subtype
of Float.

E.g. unifying two different records produces a special union datatype such that
accessing a field by name `x` on the union resolves via dynamic dispatch using
the hash-table.

This means we have a statically typed language with principal typing, meaning we
can infer types for any program even when no user type-specifiers are provided.
User type-specifiers are constraints on the solutions found by the type-solver.

This means the binding and assignment operators create a copy rather than alias.

Note that the `a |> f(args...)` operator is used as sugar for `f(a, args...)` and
is left-associative for easy chaining.

How does mutability specification work?
- If the `mut` modifier is added before a type, it means its interior may be 
  mutated. Without this qualifier, all contents are assumed to be imutable.
- If the `weak` modifier is added for a pointer/ref-cell, it means the contents
  are referenced weakly. Where ambiguous, type-solver will always generate 
  strong references, so this is an explicitly user-requested feature.

How do union types work?
- All unions are written as `T | U | V | ...`
- Can be matched out individually or restricted via built-ins, e.g. 
  ``has_field(v, `x`) = v has? x``, `v.is_ref?`, `v.is_weak_ref?`, etc. 
  `has_field` requires field name to be a const argument.

```
# module 'Robot'

# the 'export default' statement allows a type to be referenced whenever this
# module is used as a type-specifier.
export default Robot

circle_milliradians = 6283   # (3.14159 * 2) = 6.28318, rounded to 3 places

Robot_V1 =
  position
  heading
  is_pen_down
  polygons

Robot_V2 = 
  position: mut Vector2[Int]
  heading: mut Int
  is_pen_down: mut Bool
  polygons: mut List[Polygon]

Polygon =
  lines: mut List[Vector2[Int]]

Robot = Robot_V1 | Robot_V2

new() =
  Robot_V2 {
    position: Vector2[Int]{ x: 0, y: 0 },
    heading: 0,
    is_pen_down: false,
    polygons: new Polygon()
  }

move(mut robot, distance: Int) =
  old_position = robot.position
  new_position = Vector2[Int] {
    x: robot.position.x + distance * Math.cos(robot.heading),
    y: robot.position.y + distance * Math.sin(robot.heading)
  }
  if robot.is_pen_down
    new_polygon = Polygon { lines: new_list[Polygon]() }
    robot.polygons
    |> List.tail()
    |> List.append(new_polygon)

rotate_by_radians(mut robot, rotation_in_milliradians: Int) =
  robot.heading = (robot.heading + rotation_in_milliradians) % circle_milliradians

rotate_by_degrees(mut robot, rotation_in_degrees: Float) =
  robot
  |> rotate_by_radians(Int.from_float(Math.degrees(rotation_in_milliradians)))
```

Example of unions:

```
True singleton
False singleton
Bool = True | False

if_then_else(condition, if_true_thunk, if_false_thunk) =
  match condition
  | True => if_true_thunk()
  | False => if_false_thunk()
```

```
Mammal =
  birth_offspring

Reptile =
  lay_egg

get_child_1(animal) =
  match animal
  | (mammal: Mammal) => mammal.birth_offspring()
  | (reptile: Reptile) => reptile.lay_egg()

get_child_2(animal) =
  if animal has birth_offspring
    # 'animal' type is now restricted to fields with the `birth_offspring` field
    # aka smart-casting in other languages.
    animal.birth_offspring()
  elif animal has birth_offspring
    animal.lay_egg()
  else
    throw TypeError($"animal {animal} does not have any reproduction function")
```

QUESTION: do we need explicit casts? (Probably)
- advantage: enables more flexible programming where user can assert the type
  based on values else throw an exception
- disadvantage: cast-free programming is a hallmark of dynamically-typed 
  languages
