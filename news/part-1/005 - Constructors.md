May 1

It makes sense for objects to support destructors and constructors.
- Destructors are vital to clean manual memory management
- Copy and move constructors ensure memory management is efficient.
- ~~Constructors should be overloadable (unlike regular functions).~~

Rather than lump onto `Struct`, consider adding separate `Object` and 
`Interface` structures at compile-time.
- every `Object` must begin with the letter `O`
  every `Object` type has a default identity constructor, used for typing.
  structures are constructed literally.
- every `Interface` must begin with the letter `I`.
- Objects can implement interfaces to offer hooks for builtin operations.
  - e.g. `ICopy` or `IMove` or `IDestroy` to provide copy-initialization, move-initialization, 
    and de-initialization methods.
  - e.g. operator overloading
  - these can subsequently be invoked by the compiler
  - note: `std::move` in C++ also tells the compiler not to call the destructor for
    the moved expression at the end of the scope/context.
    For us, we must analyze this explicitly.
  - consider using explicit keyword unary expressions when creating/disposing:
    - `new` to invoke a class constructor
    - `move` to invoke a move constructor, ignore calling destructor for arg
    - `copy` to invoke a copy constructor
    - `delete` to invoke the destructor
- Objects are always boxed, 
  interface instances are fat pointers that are thus dynamic-dispatch capable. 
  They are much more heavy-weight than smaller data-types.
  - only objects may implement interfaces (fat pointers)
- Objects and interfaces can also be built on top of tables

```
box = module [ContentType] {
    OBox = Object (value) {
        # every `Object` type accepts a 'primary constructor'
        # the keyword type 'Self' is now defined.
        # the keyword argument 'self' may be used as the first arg to indicate a method.
        # data members are automatically computed from the closure of all 'self' methods. :)

        implements ICopy;
        implements IMove;

        value :: ContentType;
        ptr :: Opt[&mut ContentType];
        
        # note imperative elements supported: 
        # automatically run as a part of 'initialization' after definition.
        ptr = new_mem_ptr(value);
        *ptr <- value;

        copy_constructor :: Fn (Self) Self;
        move_constructor :: Fn (&mut Self) Self;

        # crucially, an object can and must contain definitions in 
        # the type specifier,
        # so the vtable is shared between instances.
        
        copy_constructor (other) = {
            new_mem_ptr = allocate_ptr(*other);
            new Object(new_mem_ptr)
        };

        move_constructor (other) = {
            new_mem_ptr = allocate_ptr(*other);
            new Object(new_mem_ptr)
        };

        # functions are only bound if they accept the 'self' keyword argument.
        # here are some methods:

        get :: Fn (Self) ContentType;
        set :: Fn (Self, ContentType) Void;

        get (self) = {
            *self.ptr
        };
        set (self, value) = {
            *self.ptr <- value;
        };

        # actually useful methods?

        # `operator 1*` is a kind of vid for '*'-- unary
        implements pointer_like.IPointerLike;
        operator 1* (self) = {
            *self.ptr
        };

        apply (self, other_box, fn) = {
            fn(*self, *other_box)
        };

        # actually useful static method:
        allocate_ptr (init_val) = {
            new_mem_ptr := alloc[ContentType].one();
            new_mem_ptr <- init_val;
            new_mem_ptr
        };
    };

    new :: Fn (ContentType) OBox;

    new (value) = {
        new_mem_ptr := alloc[ContentType].one();
        new_mem_ptr <- value;
        new OBox(new_mem_ptr)
    };
};

testing = module {

    boxed_add (v1, v2) = {
        box1 = box::new(v1);
        box2 = box::new(v2);
        box1.apply(box2, operator 2+)
    };

    move_eg () = {
        foo = box::new(42);
        bar = move foo;
    };

};
```

Introduce objects and interfaces with Astropod 1.1.
Delay it until the rest of the language is working.
Maybe it would be a good idea to assemble a roadmap?