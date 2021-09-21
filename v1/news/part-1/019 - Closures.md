May 13 - Cool Closures

In [018](018 - Rev 9.md), described that no more mutable variables.

All bindings are immutable, but an immutable binding can be made to a pointer
to mutable data (cf. ML).

Incredibly, this allows us to use implicit closures very effectively:
- every symbol is closed-over by value copy (...as if there were any other option)
- mutable symbols are represented by pointers, which can be 'closed over' without
  interfering with external mutability for the pointer
- even immutable pointers can be closed over to provide the desired behavior at a
  smaller memory footprint.
  
This means `nonlocal` declarations are no longer required.
