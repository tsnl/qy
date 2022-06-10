# 000 - Understanding the Machine

The key thing modern digital computers allow you to do is change the behavior
of a digital circuit, which reads incoming signals and sends outgoing binary signals
(called _bits_) over time. 
A CPU is the primary device within a computer, and usually takes 
control of all other devices on the machine, including peripherals like 
keyboards, mice, and displays, extension cards like network interface cards or
graphics cards, etc. 
The way the CPU does this is with memory.
By giving groups of 8 bits (or a _byte_) a unique _address_, the CPU can read some 
signals, do something based on the _value_ of those signals, and write to other
signals.
In conjunction with specialized devices that store values over time (SRAM, DRAM),
and a pre-determined rule-set that determines what to do for each instruction value,
a CPU can be _programmed_ using a list of instructions to handle a wide variety of
tasks.
For example, a CPU on a toy car may be programmed to autonomously follow a dark line
against a light background using a strip of downward-firing brightness sensors that each 
updates a 1-byte signal dozens of times a second. A CPU may be programmed to _load_
signals from a special address that the sensor's signals are _mapped_ to, compare the 
values from different sensors to determine if the line is to the left or right of the 
middle of the car, _compute_ new values by instructing the CPU to read some memories for
inputs and overwrite a no-longer-needed memory for output, and then _store_ these computed
values at special memory corresponding to the motors powering the wheels.

The key issue with addressing memories is that your addressing scheme depends on the
physical architecture of your target computer.
In the early days of digital computers, all software was tightly coupled with the hardware
it ran on. However, this makes it very difficult to distribute software, or allow users
of different computers to collaborate.
The solution is the _operating system_, which is a super-program that creates a _virtual_
computer whose characteristics are largely decoupled from the hardware they operate on.
Now, developers can write software for a particular OS instead of a particular machine, 
relying on the OS to dynamically translate their instructions on a virtual computer into
instructions for a physical machine.
For example, a computer may only have 640KB of memory available via RAM chips, but a large
amount of memory available via a slower disk-based hard-drive. Modern PC operating
systems provide 'virtual memory' which allows developers to pretend they have infinite
memory: the OS will automatically distribute memory in use between the RAM and the 
hard-drive, giving more frequently used data the faster memory.

OSes also handle most of the hard work involved in connecting to different devices, providing
developers a common view of multiple devices. For example, two computer mice connected to
different ports (say USB and PS/2) use completely different protocols to communicate with
the computer they are connected to: the OS takes care of this for you, and turns these raw
signals into memories you can access describing mouse cursor movement, position, and other
more meaningful values.

Qy is a programming language. All this means is that we make writing computer instructions
a little easier by taking care of boilerplate and helping you find errors using logic.
A program called the _compiler_ translates Qy instructions into assembly.
This means Qy can be used to write programs that run on an OS or directly on a specific
hardware platform.

In summary, 
- programming is the art of instructing a piece of electronics to move memory 
  around according to well-defined rules. 
- A program that does not produce _any_ output when run is indiscernable from running no 
  program at all: thus, the primary focus should always be on how to transform input data
  into output data.

In the following chapters, we will learn these rules and their representations in Qy, as
well as some common idioms that Qy makes easier via special syntax.

---

FURTHER READING

-   "Ch13: Address Spaces" from Operating Systems in Three Easy Pieces <br/>
    https://pages.cs.wisc.edu/~remzi/OSTEP/vm-intro.pdf


-   Von Neumann Architecture, Harvard Architecture
-   