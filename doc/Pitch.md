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
  - the unary `*` type operator unboxes an instance while the unary `*` value
    operator creates a shallow copy. 
    - All data-types are boxed by default, including primitives like `Int`, 
      `Float`, `Double`, etc. This allows us to cast them to `Object` trivially.
    - Fixed-length arrays (`Array[T, n]`) can be unboxed into an inline 
      representation. Variable-length arrays (`List[T]`) can be unboxed too, but 
      this only unboxes similar to C++ `std::vector<T>* -> std::vector<T>`.
    - Compiler does not optimize referential transparency into unboxing; let the
      user do it, maybe provide a warning/hint.
    - `Any` cannot be unboxed. `weak T` cannot be unboxed.
  - if type-specifier not provided, then compiler uses type-inference to guess,
    defaulting to the `Any` datatype on join, adding a `*` prefix only in cases
    of referential transparency and non-`Any`
- Shift to first-class reference-counting with support for weak references and
  mutability specifiers as **variable-level properties** (instead of type)
  - assignment always re-binds slots, so `mut` only controls slot mutability,
    not exterior mutability via slot/interior mutability of boxed instance.
    `mut` is the opposite of C#'s `readonly`
  - exception: when `mut id: *T`, then 're-binding' the slot involves 
    overwriting the datum, exactly like a value type.
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
use Math;
use Gfx;

pi = 3.14159;

Vec2F = (x: Float, y: Float);
Robot = (position: *Vec2F, angle_deg: Float, pen_down: Bool);

Robot.new_default () = {
  Robot(Vec2F(0, 0), 0, Bool.False);
};
Robot.pen_down (self) () = {
  self.pen_down = Bool.True;
};
Robot.pen_up (self) () = {
  self.pen_down = Bool.false;
};
Robot.walk (self) (distance_px) = {
  src_x = self.x;
  src_y = self.y;
  dst_x = self.x + distance_px * Math.cos(Math.radians(self.angle));
  dst_y = self.y + distance_px * Math.sin(Math.radians(self.angle));
  src_pt = Vec2f.new(src_x, src_y);
  dst_pt = Vec2f.new(dst_x, dst_y);
  if (self.pen_down) {
    Gfx.draw_line(src_pt, dst_pt);
  };
  self.position = dst_pt;
};
Robot.turn (self) (angle_offset_deg) = {
  self.angle_deg += angle_offset_deg;
};

Robot.draw_square (side_length_in_px) = {
  robot = Robot.new_default();
  robot.pen_down();
  for i in range(4) {
    robot.walk(side_length_in_px);
    robot.turn(90);
  };
};
```

```
# example 2

Bool = {True, False};

Friend = {
  BestFriend,
  Friend(index: Int, name: String)
};
RegularFriendInfo = (email_id: String, phone_number: PhoneNumber);
RegularFriendInfoList = List[RegularFriendInfo];
PhoneNumber = (international_code: UByte, area_code: UShort, suffix: UInt);

Program = (
  regular_friend_info_list: RegularFriendInfoList,
  former_friends_count: Int
);

# entry points are special; 'main' is a built-in keyword, and is the only 
# function you can define at a top-level.
StringList = List[String];
main (args: StringList) = {
    # ...
};
```

```
# example 3: templates, fixed-size arrays

List [ElemType] = (
  data: UnsafePointer[ElemType],
  count: ISize
);

NamedList [ElemType] = (
  slots: List[ElemType],
  name_index_map: HashMap[String, ISize]
);

Vector [ElemType, elem_count: ISize] = (
  slots: *Array[ElemType, elem_count]
);

# note that template arguments for the 'self' type are automatically introduced
# into scope here
NamedArray.push (self) (name: String, v: ElemType) = {
  assert !self.name_index_map.contains_key(name);
  self.name_index_map.insert(name, self.slots.length);
  self.slots.push(v);
};

# note that methods can also take template arguments
# the `.convert_to[T]()` method is used to cast.
NamedArray.map_convert_to [T] (self) () = {
  # ...
};
```

```
# example 4: weak references

DoublyLinkedList [T] = {
  prev: weak DoublyLinkedList[T],
  next: DoublyLinkedList[T],
  head: T
};
```

Weak reference instances have a method called `acquire()` that returns an
`Option[T]` instance where the `Some` case is a strong reference.

Weak references cannot be unboxed.

---

## Implementation plan

**PHASE 1: pure dynamic**

Implement a purely duck-typed language, so every instance is an instance of 
`Any`. Every dynamic dispatch hash-map key is an IntStr.

User can still bind type expressions for ADTs, these are used to define 
constructors.

At this stage, there is no way to protect against reference cycles or to enforce
immutability. We could provide `Any`, `weak Any`, `weak mut Any`, etc. but this
would require type-checking which is a non-goal for ths phase.

TODO: add support for exceptions and exception handling at this stage.

**PHASE 2: monomorphic gradual typing**

Support type annotations, including `weak mut T`, `*T`.

Implement checked type conversions. Conversions from `Any` to a non-`Any` type
are checked at run-time, including implicit conversions at function call 
boundaries. 

Support a few built-in polymorphic datatypes like `List[T]`, `Array[T,n]`,
`Span[T]`, `HashMap[K, V]`, and `HashSet[T]`.

**PHASE 3: templates**

Support template type arguments.

Support literals and global constants for template values. No evaluation.

