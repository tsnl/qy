Qy-2.1 succeeded in its goals, it just had the wrong goals.

Without going into too much detail, explicit manual allocation and a reliance on 
macros for high-level features are good in theory but terrible in practice; 
there's so much work required to create basic abstractions from scratch each 
time.

Furthermore, using Qy is a lot more like using a typed dialect of assembly,
and there is a muddled conception of register types, value types, and data 
pushed to the stack.

Because it was so inconvenient to use, there was no chance of replacing Python
with Qy.

At least the experience taught me to focus on productivity with a path to
performance.

I have spent a long time prototyping solutions, and I think I have something
better.

In summary...
- Shift to gradual typing and a universally boxed object model where the 
  compiler decides where to allocate memory based on escape analysis.
  - there is an 'Any' datatype which offers dynamic typing via duck-dispatch,
    i.e. using a hash-map like Python.
    - this can be optimized in the future with compile-time interfaces.
  - the unary `*` value operator creates a shallow copy. 
  - if type-specifier not provided, then compiler uses type-inference to guess,
    defaulting to the `Any` datatype on join, adding a `*` prefix only in cases
    of referential transparency and non-`Any`
- Shift to first-class reference-counting with support for weak references and
  mutability specifiers as **variable-level properties** (instead of type)
  - assignment always re-binds slots, so `mut` only controls slot mutability,
    not exterior mutability via slot/interior mutability of boxed instance.
    `mut` is the opposite of C#'s `readonly`
  - no arguments can be marked as `mut` since these slots cannot be re-bound
- Every function is a method (but not a closure)
  - closures can be provided with functors (ahh, C++ before C++11)
  - the user only defines methods that operate on a specific piece of state
    - these may also behave like properties
    - cannot define methods on union datatypes
  - there are no global variables: top-level definitions either types, methods,
    or immutable constant bindings.
  - `self` is a built-in keyword argument
- Interfaces will be supported in a future version of the language to enable
  dynamic dispatch without duck dispatch.

```
# example 1

# note that there is a global namespace, module names must start with uppercase
# letters, and each file is a singleton type that may contain other types.
# note the TId/vid distinction.
use Math
use Gfx

pi: Float = 3.14159

Vec2F: struct = 
  mut x: Float
  mut y: Float

Robot: record = 
  mut position: Vec2F
  mut angle_deg: Float 
  mut pen_down: Bool

Robot.new_default () =
  Robot {
    position: Vec2F { x: 0, y: 0 }, 
    angle_deg: 0, 
    pen_down: Bool.False
  }

Robot.pen_down (self) () =
  self.pen_down := Bool.True

Robot.pen_up (self) () =
  self.pen_down := Bool.false

Robot.walk (self) (distance_px) =
  src_x = self.x
  src_y = self.y
  dst_x = self.x + distance_px * Math.cos(Math.radians(self.angle))
  dst_y = self.y + distance_px * Math.sin(Math.radians(self.angle))
  src_pt = Vec2f { x: src_x, y: src_y }
  dst_pt = Vec2f { x: dst_x, y: dst_y }
  if (self.pen_down)
    Gfx.draw_line(src_pt, dst_pt)
  self.position := dst_pt

Robot.turn (self) (angle_offset_deg) =
  self.angle_deg += angle_offset_deg

Robot.draw_square (side_length_in_px) =
  robot = Robot.new_default()
  robot.pen_down()
  for i in range(4)
    robot.walk(side_length_in_px)
    robot.turn(90)
```

```
# example 2

Bool: variant = 
  True 
  False

Friend: variant = 
  BestFriend
  RegularFriend(index: Int, name: String)

RegularFriendInfo: record = 
  email_id: String
  phone_number: PhoneNumber

PhoneNumber: record = 
  international_code: UByte
  area_code: UShort
  suffix: UInt

Program: record = 
  regular_friend_info_list: List[RegularFriendInfo]
  former_friends_count: Int

# entry points are special; 'main' is a built-in keyword, and is the only 
# function you can define at a top-level.
main (args: List[String]) =
  # ...
```

```
# example 3: templates, fixed-size arrays

List[ElemType]: record = 
  data: UnsafePointer[ElemType]
  count: ISize

NamedList[ElemType]: record = 
  slots: List[ElemType]
  name_index_map: HashMap[String, ISize]

Vector[ElemType, elem_count: ISize]: record = 
  slots: Array[ElemType, elem_count]

# note that template arguments for the 'self' type are automatically introduced
# into scope here
NamedArray.push (self) (name: String, v: ElemType) =
  assert !self.name_index_map.contains_key(name)
  self.name_index_map.insert(name, self.slots.length)
  self.slots.push(v)

# note that methods can also take template arguments
# the `.convert_to[T]()` method is used to cast.
NamedArray.map_convert_to [T] (self) () =
  # ...
```

```
# example 4: weak references

DoublyLinkedList[T]: record = 
  weak prev: DoublyLinkedList[T]
  next: DoublyLinkedList[T]
  head: T
```

Weak reference instances have a method called `acquire()` that returns an
`Option[T]` instance where the `Some` case is a strong reference.

Weak references cannot be unboxed.

There are no type aliases, partly because this would cause syntactic ambiguity
(between enum definition and alias), partly because it creates a lot of 
additional confusion, partly because encapsulation will do the job better in
most cases (creating a distinct type instance).

---

## Implementation plan

**PHASE 1: monomorphic typing**

Support type annotations, e.g. `weak mut T`

Implement checked type conversions. Conversions from `Any` to a non-`Any` type
are checked at run-time, including implicit conversions at function call 
boundaries. 

Support a few built-in polymorphic datatypes like `List[T]`, `Slice[T]`,
`Span[T]`, `HashMap[K, V]`, and `HashSet[T]`.

**PHASE 2: templates**

Support template type arguments.

Support literals and global constants for template values. No evaluation.
