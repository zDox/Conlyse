#version 330 core
layout (location = 0) in vec2 position;

out vec2 vPosition;

void main()
{
    vPosition = position;  // Just pass through, don't transform yet!
}