# -*- coding: utf-8 -*-
# This file is part of the python-asyncdgt library.
# Copyright (C) 2015 Niklas Fiekas <niklas.fiekas@tu-clausthal.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY and FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""
The asyncdgt library.
Copyright (C) 2015 Niklas Fiekas <niklas.fiekas@tu-clausthal.de>

Usage:
  python -m asyncdgt [--debug] <dgt-port>

[--debug]
  Enable debug logger.

<dgt-port>
  The serial port with the DGT board.
"""

import asyncio
import asyncdgt
import logging
import sys
import serial
import serial.tools.list_ports


def usage():
    # Print usage information.
    print(__doc__.strip())

    # List the available ports.
    print("  Probably one of:")
    for dev, name, info in serial.tools.list_ports.comports():
        print(f"  * {dev} ({info})")

    return 1


async def main_async(port_globs):
    """
    Main asynchronous function to handle DGT board connection and events.
    """
    loop = asyncio.get_running_loop() # Get the current running event loop

    dgt = await asyncdgt.auto_connect(loop, port_globs)

    @dgt.on("connected")
    def on_connected(port):
        print(f"Board connected to {port}!")

    @dgt.on("disconnected")
    def on_disconnected():
        print("Board disconnected!")

    @dgt.on("board")
    def on_board(board):
        print("Position changed:")
        print(board)

    @dgt.on("button_pressed")
    def on_button_pressed(button):
        print(f"Button {button} pressed!")

    @dgt.on("clock")
    def on_clock(clock):
        print("Clock status changed:", clock)

    # Give auto_connect some time to establish a connection.
    # We await dgt.connected.wait() inside the individual get/set functions,
    # but a small initial sleep can help ensure the background connection task starts.
    # Alternatively, you could await dgt.connected.wait() here once.
    await asyncio.sleep(0.1) # Small delay to let auto_connect initiate connection

    # Get some information.
    try:
        print("Version:", await dgt.get_version())
        print("Serial:", await dgt.get_serialnr())
        print("Long serial:", await dgt.get_long_serialnr())
        board = await dgt.get_board()
        print("Board:", board.board_fen())
    except asyncio.CancelledError:
        print("Connection or information retrieval cancelled.")
        return
    except Exception as e:
        print(f"Error getting board information: {e}")
        # Depending on desired behavior, you might want to exit or continue
        # if initial connection fails. For now, we'll try to continue.


    # Get the clock version.
    try:
        print("Clock version:", await asyncio.wait_for(dgt.get_clock_version(), 1.0))
    except asyncio.TimeoutError:
        print("Clock version request timed out.")
    except Exception as e:
        print(f"Error getting clock version: {e}")

    # Display some text.
    print("Displaying text ...")
    quote = "Now, I am become death, the destroyer of worlds. Ready"
    await clock_display_sentence(dgt, quote)

    # Let the clock beep.
    try:
        print("Beep ...")
        await asyncio.wait_for(dgt.clock_beep(0.1), 1.0)
    except asyncio.TimeoutError:
        print("Beep not acknowledged in time.")
    except Exception as e:
        print(f"Error making clock beep: {e}")


    # Start a countdown.
    try:
        print("Countdown ...")
        await asyncio.wait_for(dgt.clock_set(left_time=10, right_time=7, left_running=True), 1.0)
    except asyncio.TimeoutError:
        print("Clock does not respond.")
    except Exception as e:
        print(f"Error setting clock countdown: {e}")


    # Run the event loop.
    print("Running event loop ... Press Ctrl+C to exit.")
    try:
        # In newer Python versions, `run_forever` is less commonly used directly
        # for simple scripts. Instead, you'd typically await a long-running task
        # or use a sentinel like an Event that never gets set.
        # For an interactive example like this, `run_forever` is still suitable
        # if `main_async` doesn't contain the core infinite loop logic.
        # However, to gracefully shut down tasks on Ctrl+C, a cleaner approach
        # is to explicitly create a cancellable task for `main_async` itself.
        # But for this example, we'll keep `run_forever` and handle cleanup.
        await asyncio.Future() # Await a Future that never completes, effectively running forever
    except asyncio.CancelledError:
        print("\nEvent loop cancelled (e.g., via Ctrl+C). Shutting down...")
    finally:
        dgt.close() # This will trigger the 'disconnected' event and stop driver threads

        # Get all tasks and cancel them gracefully.
        # asyncio.Task.all_tasks() is deprecated. Use asyncio.all_tasks()
        pending = asyncio.all_tasks(loop=loop) # Specify loop for clarity, though optional from 3.10+
        for task in pending:
            task.cancel() # Request cancellation

        # Wait for all tasks to complete, ignoring CancelledError
        await asyncio.gather(*pending, return_exceptions=True)
        loop.close()
        print("Event loop closed.")

    return 0


async def clock_display_sentence(dgt, sentence):
    for word in sentence.split():
        await asyncio.sleep(0.2) # Use await

        try:
            await asyncio.wait_for(dgt.clock_text(word), 0.5) # Use await
        except asyncio.TimeoutError:
            print("Sending clock text timed out.")
        except Exception as e:
            print(f"Error sending clock text: {e}")


def main_entrypoint():
    if "--debug" in sys.argv:
        logging.basicConfig(level=logging.DEBUG)

    port_globs = [arg for arg in sys.argv[1:] if arg != "--debug"]
    if not port_globs:
        sys.exit(usage())
    else:
        # Use asyncio.run() for Python 3.7+ to manage the event loop lifecycle
        # For Python 3.13, this is the standard way to run the top-level async function.
        sys.exit(asyncio.run(main_async(port_globs)))


if __name__ == "__main__":
    main_entrypoint()
