Criticisms of Pitch1:
- user winds up authoring interfaces, records, and type-specified functions just
  like in a manifestly typed language.

Better idea
- Remove explicit interfaces, lean into dynamic typing
- Use a hash-map to resolve fields (duck-typing), but ensure that each field
  name is baked out as an interned symbol ahead of time. This makes hash-map
  lookups much more efficient, esp. with a high load-factor hash-map like
  Robin-hood hashing with linear probing.
- Each datatype can encapsulate highly packed data that is de-referenced by a
  virtual table.
- User can only define 'trait' to qualify with type-specifiers, concrete 
  data-structures are created in an ad-hoc way and checked based on runtime type
  constraints. <br/>
  IDEA: further enforce that bindings are immutable, such that `:=` just updates
  datums in-place rather than re-binds.
```
# module 'Robot'

using Math;

const CIRCLE_MILLIRADIANS = 6283

trait Robot(x, y, heading, is_pen_down)

union Bool:
  True
  False

function new() -> Robot:
  { x=0, y=0, heading=0, is_pen_down=Bool.True }

function pen_down(robot: Robot):
  robot.is_pen_down := Bool.True

function pen_up(robot):
  robot.is_pen_down := Bool.False

function move(robot, distance):
  robot.x := robot.x + Math.cos(robot.heading) * distance
  robot.y := robot.y + Math.sin(robot.heading) * distance

function rotate_by_radians(robot: Robot, rotation_radians):
  robot.heading := (robot.heading + rotation_radians) % CIRCLE_MILLIRADIANS

function rotate_by_degrees(robot: Robot, rotation_degrees):
  robot:rotate_by_radians(Math.degrees(rotation_degrees))
```
